import random
import asyncio
import json
import discord
from discord.ext import commands
from discord.utils import get
from config import *

settings = get_settings()
plants = get_plants()
players = get_players()
babki_running = True
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=settings['prefix'], intents=intents, help_command=None)
users = []


def save(users=players):
    with open('data/players.json', mode='w', encoding='utf-8') as json_file:
        json_file.write(json.dumps(users, ensure_ascii=False))


def load_players():
    global players
    players = get_players()


async def not_authorized(ctx):
    await ctx.send(embed=discord.Embed(color=discord.Colour.red(), title='Ошибочка!',
                                       description=f'Вы не в игре!. '
                                                   f'Для начала используйте команду '
                                                   f'"{settings["prefix"]}join_game"'))


def get_commission(id):
    return (100 - players[str(id)]["reputation"]) * 50


def add_rep(id, rep):
    if players[str(id)]["reputation"] + rep > 100:
        players[str(id)]["reputation"] = 100
    else:
        players[str(id)]["reputation"] += rep


def take_rep(id, rep):
    if players[str(id)]["reputation"] - rep < 0:
        players[str(id)]["reputation"] = 0
    else:
        players[str(id)]["reputation"] -= rep


def get_garden_cost(id):
    return players[str(id)]["garden bed"] * 10000


def get_defence_cost(defence_lvl):
    if defence_lvl < 20:
        return 3500, defence_lvl + 5
    elif 20 <= defence_lvl < 40:
        return 8000, defence_lvl + 5
    elif 40 <= defence_lvl < 60:
        return 10000, defence_lvl + 5
    elif 60 <= defence_lvl < 80:
        return 15000, defence_lvl + 2
    else:
        return False, 0


def get_price_to_lvl_up(lvl):
    # lvl: (exp_needed, update_price)
    costs = {
        1: (150, 220),
        2: (390, 450),
        3: (680, 550),
        4: (870, 1500),
        5: (990, 3000),
        6: (1150, 4000),
        7: (1290, 5000),
        8: (1350, 6000),
        9: (1610, 10000),
        10: (1940, 15000),  # experemental
        11: (2080, 30000),
        12: (None, None)
    }
    return costs[lvl]


async def no_money(ctx):
    await ctx.send(embed=discord.Embed(color=discord.Colour.red(), title='Ошибка!', description="Недостаточно денег!"))


async def custom_error(ctx, error):
    await ctx.send(embed=discord.Embed(color=discord.Colour.red(), title='Ошибка!', description=error))


@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')
    await babki_babki_babki()


# @bot.command()
# async def help(ctx):
#     embed = discord.Embed(color=discord.Color.blurple(), title='Игровые команды')  # Создание Embed'a
#     embed.add_field(name='* Игра *', value='join_game\n disconnect_game')
#     embed.add_field(name='* Ферма *', value='hero\n inventory\n money')
#     embed.add_field(name='* Казино *', value='dice')
#     await ctx.send(embed=embed)


@bot.command()
async def hello(ctx):
    author = ctx.message.author
    await ctx.send(f'Hello, {author.mention}!')


@bot.command()
async def save_data(ctx):
    save()
    await ctx.message.add_reaction('✅')


def check_message(author):
    def inner_check(message):
        if message.author == author:
            return message.content
        else:
            return None

    return inner_check


@bot.command(aliases=['new_player'], description='Создает нового персонажа')
async def join_game(ctx):
    global settings

    id = ctx.author.id
    if str(id) not in players.keys():
        # save hero
        players[str(id)] = {
            "money": 100,
            "income": 0,
            "reputation": 100,
            "defence": 0,
            "exp": 0,
            "level": 1,
            "garden bed": 1,
            "theft skill": 0,
            "buildings": {}
        }

        # сохраняем изменения

        embed = discord.Embed(color=discord.Colour.green(),
                              title=f'Поздравляем!',
                              description='Добро пожаловать в жестокий, кровавый и '
                                          'безжалостный мир денег!')  # Создание Embed'a
        await ctx.send(embed=embed)

    else:
        embed = discord.Embed(color=discord.Colour.orange(), title='Вы уже в игре!',
                              description='Невозможно создать нового персонажа '
                                          'находясь в игре, для начала нужно удалить старого!')  # Создание Embed'a
        await ctx.send(embed=embed)


@bot.command(description='Удаляет вашего персонажа из игры')
async def disconnect_game(ctx):
    id = ctx.author.id

    if str(id) in players.keys():
        embed = discord.Embed(color=discord.Colour.red(), title='Подтвердите выход из игры',
                              description='Вы уверены что хотите выйти из игры?')  # Создание Embed'a
        msg = await ctx.send(embed=embed)

        emoji = ['🚫', '✅']
        [await msg.add_reaction(e) for e in emoji]

        reaction, msg = await bot.wait_for('reaction_add', timeout=30)
        while str(reaction.emoji) not in emoji or str(msg.id) != str(id):
            reaction, msg = await bot.wait_for('reaction_add', timeout=30)
        if str(reaction.emoji) == '✅':
            del players[str(id)]
            # сохраняем изменения

            await ctx.send(embed=discord.Embed(color=discord.Colour.green(), title='Эхх',
                                               description='Жаль, а нам было весело, но ничего, '
                                                           'еще увидимся, всего хорошего!'))
        else:
            await ctx.send(embed=discord.Embed(color=discord.Colour.red(), title='Фуух',
                                               description='Как хорошо что вы передумали, у нас еще все впереди!'))
    else:
        await not_authorized(ctx)


@bot.command(aliases=['dice_with'], description='Позволяет играть с другими игроками в кости на монеты')
async def dice(ctx, amount: int, member: discord.Member):
    id = ctx.author.id
    ids_of_players = players.keys()

    if str(id) in ids_of_players and str(member.id) in ids_of_players:  # если оба участника находятся в игре
        if str(id) != str(member.id):  # если вызывающий участник не вызывает на игру сам себя

            # game accept
            embed = discord.Embed(color=discord.Colour.orange(), title='🎲Подтвердите игру',
                                  description=f'{member.mention} согласны ли вы играть?')  # Создание Embed'a
            msg = await ctx.send(embed=embed)

            emoji = ['🚫', '✅']
            [await msg.add_reaction(e) for e in emoji]

            reaction, msg = await bot.wait_for('reaction_add', timeout=30)
            while str(reaction.emoji) not in emoji or str(msg.id) != str(member.id):
                reaction, msg = await bot.wait_for('reaction_add', timeout=30)

            if str(reaction.emoji) == '✅':  # if accept
                if players[str(id)]['money'] >= amount and players[str(member.id)]['money'] >= amount:
                    # game dice
                    author_nums = [random.randint(1, 6), random.randint(1, 6)]
                    member_nums = [random.randint(1, 6), random.randint(1, 6)]
                    await ctx.send(
                        f'🎲**{ctx.author.name}** делает ставку в размере **{str(amount)}**🪙, а **{member.name}** '
                        f'принимает ее, игра начинается...')
                    await asyncio.sleep(2)
                    await ctx.send(
                        f'🎲**{ctx.author.name}** выбрасывает **{author_nums[0]}** и **{author_nums[1]}**...')
                    await asyncio.sleep(3)
                    await ctx.send(
                        f'🎲**{member.name}**, бросает кости... и выбрасывает **{member_nums[0]}** и **{member_nums[1]}**...')
                    await asyncio.sleep(2)

                    # who wins
                    if sum(author_nums) > sum(member_nums):
                        await ctx.send(f'**{ctx.author.name}** побеждает! И выигрывает **{amount}**🪙')

                        # give amount to winner from loser
                        players[str(member.id)]['money'] -= amount
                        players[str(id)]['money'] += amount
                    elif sum(author_nums) < sum(member_nums):
                        await ctx.send(f'**{member.name}** побеждает! И выигрывает **{amount}**🪙')

                        # give amount to winner from loser
                        players[str(member.id)]['money'] += amount
                        players[str(id)]['money'] -= amount
                    else:
                        await ctx.send(f'**Ничья!** **{str(amount)}**🪙 уходят на счет казино')
                        players[str(member.id)]['money'] -= amount
                        players[str(id)]['money'] -= amount
                    players[str(id)]['exp'] += 5
                    players[str(member.id)]['exp'] += 5
                    # save changes

                else:
                    await ctx.send(embed=discord.Embed(color=discord.Colour.red(), title='🎲Нет маней в кармане!',
                                                       description=f'Проверьте карманы, '
                                                                   f'возможно в них дырка или у вас украли деньги!'))
            else:
                await ctx.send(embed=discord.Embed(color=discord.Colour.orange(), title='🎲Отказ',
                                                   description=f'{member.mention} отказался играть в кости с {ctx.author.mention}'))
        else:
            await ctx.send(embed=discord.Embed(color=discord.Colour.red(), title='🎲Ага, попался!',
                                               description=f'{ctx.author.mention} попытался обмануть'
                                                           f' казино и поплатился за это, теперь у него **0**🪙'))
            players[str(id)]['money'] = 0
            # сохраняем изменения

    else:
        await ctx.send(embed=discord.Embed(color=discord.Colour.red(), title='🎲Не в игре!',
                                           description=f'Один из участников игры находится вне игры!'
                                                       f' Для начала используйте команду "{settings["prefix"]}join_game"'))


@bot.command(aliases=['moneys', 'coins', 'babki'], description='Показывает монеты вашего персонажа')
async def money(ctx):
    id = ctx.author.id
    if str(id) in players.keys():
        embed = discord.Embed(color=discord.Colour.blue(), title='👛Кошелёчек',
                              description=f'У вас **{round(players[str(id)]["money"], 2)}**🪙')
        await ctx.send(embed=embed)
    else:
        await not_authorized(ctx)


@bot.command()
async def plant(ctx):
    id = ctx.author.id

    if str(id) in players.keys():  # если user есть в БД
        level = players[str(id)]['level']
        rep_delta = get_commission(str(id))
        # выбираем рассаду
        embed = discord.Embed(color=discord.Colour.dark_blue(), title='1) Выбор рассады',
                              description=f"На вашем уровне {level} доступны следующие постройки:")

        from_level = level - 6
        if from_level < 1:
            from_level = 1
        print(from_level, level)
        for lvl in range(from_level, level + 1):
            for key in plants['levels'][str(lvl)].keys():
                embed.add_field(name=key,
                                value=f'Цена: {plants["levels"][str(lvl)][key]["price"]}🪙\n'
                                      f'Доход в сек: {plants["levels"][str(lvl)][key]["power"]}🪙\n'
                                      f'Максимум в грядке: {plants["levels"][str(lvl)][key]["max"]}')
        embed.add_field(name='Комиссия:', value=f'{rep_delta}🪙')
        await ctx.send(embed=embed)

        msg = await bot.wait_for('message', check=check_message(ctx.author), timeout=30)
        while msg.content not in plants['levels'][str(level)].keys():
            msg = await bot.wait_for('message', check=check_message(ctx.author), timeout=30)

        item_to_buy = msg.content  # получаем товар который хоти приобрести

        if players[str(id)]["money"] >= plants["levels"][str(level)][item_to_buy][
            "price"] + rep_delta:  # если хватает денег то продолжаем
            embed = discord.Embed(color=discord.Colour.orange(), title='2) Подтвердите покупку',
                                  description=f'После покупки "{item_to_buy}" со счета '
                                              f'спишется {plants["levels"][str(level)][item_to_buy]["price"] + rep_delta}🪙')
            embed_msg = await ctx.send(embed=embed)

            emoji = ['🚫', '✅']
            [await embed_msg.add_reaction(e) for e in emoji]
            reaction, message = await bot.wait_for('reaction_add', timeout=30)
            while str(reaction.emoji) not in emoji or str(message.id) != str(ctx.author.id):
                reaction, message = await bot.wait_for('reaction_add', timeout=30)

            if str(reaction.emoji) == '✅':  # если согласны на покупку
                try:  # TODO fix this shit
                    can_plant = players[str(id)]["garden bed"] * plants["levels"][str(level)][item_to_buy]["max"] > \
                                players[str(id)]["buildings"][item_to_buy]
                except KeyError:
                    can_plant = True

                if can_plant:  # может ли пользователь посадить еще ед товара?
                    players[str(id)]["money"] -= plants["levels"][str(level)][item_to_buy]["price"] + rep_delta
                    players[str(id)]["income"] += plants["levels"][str(level)][item_to_buy]["power"]

                    if item_to_buy in players[str(id)]["buildings"].keys():
                        players[str(id)]["buildings"][item_to_buy] += 1
                    else:
                        players[str(id)]["buildings"][item_to_buy] = 1
                    players[str(id)]['exp'] += 20
                    await ctx.send(
                        embed=discord.Embed(color=discord.Colour.green(), title='3) Успешно, поздравляем с покупкой!'))
                    add_rep(id, 8)
                else:  # если пользователь не может этого сделать
                    await ctx.send(embed=discord.Embed(color=discord.Colour.red(), title='3) Ошибка!',
                                                       description='У вас максимальное количество данного товара '
                                                                   'и вы больше не можете его садить. '
                                                                   'Для продолжения требуется купить грядку.'))
            else:  # если не согласны
                await ctx.send(embed=discord.Embed(color=discord.Colour.red(), title='3) Покупка отменена!'))

        else:  # если не хватает денег
            await no_money(ctx)
    else:
        await not_authorized(ctx)


@bot.command(aliases=['garden'])
async def my_garden(ctx):
    id = ctx.author.id

    if str(id) in players.keys():
        embed = discord.Embed(color=discord.Colour.blue())
        embed.add_field(name='🪙Монеты', value=f'{round(players[str(id)]["money"], 2)}')
        embed.add_field(name='💸Доход', value=f'{round(players[str(id)]["income"], 2)}/сек')
        embed.add_field(name='🤝Репутация', value=f'{players[str(id)]["reputation"]}')
        embed.add_field(name='🪴Уровень садоводства',
                        value=f'LvL: {players[str(id)]["level"]}\n Exp: {players[str(id)]["exp"]}/{get_price_to_lvl_up(players[str(id)]["level"])[0]}')
        embed.add_field(name='🛡️Уровень защиты', value=f'{players[str(id)]["defence"]}')
        embed.add_field(name='🚔Уровень воровства', value=f'{players[str(id)]["theft skill"]}')

        p = [f'{key} - {players[str(id)]["buildings"][key]}шт' for key in players[str(id)]["buildings"].keys()]
        if len(p) == 0:
            p = ['* Пусто *']

        embed.add_field(name='🌲Саженцы', value='\n'.join(p))
        embed.add_field(name='🏡Грядки', value=f'{players[str(id)]["garden bed"]}шт')

        await ctx.send(embed=embed)
    else:
        await not_authorized(ctx)


@bot.command(aliases=['buy', 's'])
async def shop(ctx):
    id = ctx.author.id

    if str(id) in players.keys():
        commission = get_commission(str(id))
        cost, to_level_up = get_defence_cost(players[str(id)]["defence"])
        theft_cost, to_theft_level_up = get_defence_cost(players[str(id)]["theft skill"])
        theft_cost //= 1.5

        garden_price = get_garden_cost(str(id))

        embed = discord.Embed(color=discord.Colour.blue(), title='🛒 Магазин', description=f'Комиссия: {commission}')
        embed.add_field(name='🛡️Улучшить систему безопасности',
                        value=f'**{players[str(id)]["defence"]}lvl -> {to_level_up}lvl**\nЦена: {cost}\n')
        embed.add_field(name='💻Пройти онлайн тренинг по воровству',
                        value=f'**{players[str(id)]["theft skill"]}lvl -> {to_theft_level_up}lvl**\nЦена: ~~{theft_cost * 1.5}~~ {theft_cost}\n Без комиссии!\n 33% SALE!!')
        embed.add_field(name='🏡Купить грядку', value=f'Цена: {garden_price}')

        player_lvl = players[str(id)]["level"]
        to_lvl_up = get_price_to_lvl_up(player_lvl)
        embed.add_field(name='⏫Повысить уровень',
                        value=f'**{player_lvl}lvl -> {player_lvl + 1}lvl**\n Цена: {to_lvl_up[1]}')
        msg = await ctx.send(embed=embed)

        emoji = ['🛡️', '🏡', '⏫', '💻']
        [await msg.add_reaction(e) for e in emoji]

        reaction, msg = await bot.wait_for('reaction_add', timeout=30)
        while str(reaction.emoji) not in emoji or str(msg.id) != str(id):
            reaction, msg = await bot.wait_for('reaction_add', timeout=30)

        if str(reaction.emoji) == '🛡️':
            if players[str(id)]["money"] >= cost + commission:
                players[str(id)]["defence"] = to_level_up
                players[str(id)]["money"] -= cost + commission
                players[str(id)]["exp"] += 20

                embed = discord.Embed(color=discord.Colour.blue(), title='🛡️Система безопасности обновлена!',
                                      description=f'Теперь у вас SecuritySystemUltra++ V.{players[str(id)]["defence"]}')
                await ctx.send(embed=embed)
                add_rep(id, 8)
            else:
                await no_money(ctx)
        elif str(reaction.emoji) == '🏡':
            if players[str(id)]["money"] >= garden_price + commission:
                embed = discord.Embed(color=discord.Colour.blue(), title='🏡Успешно',
                                      description=f'Теперь у вас {players[str(id)]["garden bed"] + 1} грядки!')
                await ctx.send(embed=embed)
                players[str(id)]["garden bed"] += 1
                players[str(id)]["money"] -= garden_price + commission
                players[str(id)]["exp"] += 50
                add_rep(id, 10)
            else:
                await no_money(ctx)
        elif str(reaction.emoji) == '⏫':
            if players[str(id)]["money"] >= to_lvl_up[1] + commission:
                if players[str(id)]["exp"] >= to_lvl_up[0]:
                    embed = discord.Embed(color=discord.Colour.blue(), title='⏫Level Up!',
                                          description=f'Теперь ваш уровень {players[str(id)]["level"] + 1}')
                    await ctx.send(embed=embed)
                    players[str(id)]["level"] += 1
                    players[str(id)]["money"] -= to_lvl_up[1] + commission

                    add_rep(id, 10)
                else:  # no exp
                    await custom_error(ctx, "Недостаточно опыта!")
            else:  # no money
                await no_money(ctx)
        elif str(reaction.emoji) == '💻':
            if players[str(id)]["money"] < theft_cost:
                await no_money(ctx)
                return

            if random.choice([True, False]):  # if scum site :)
                embed = discord.Embed(color=discord.Colour.orange(), title='Упс...',
                                      description=f'Сайт онлайн тренинга оказался сCUMмом!')
                img = discord.File("source/img/scum.jpeg", filename="scum.jpeg")
                embed.set_image(url="attachment://scum.jpeg")
                await ctx.send(file=img, embed=embed)
                players[str(id)]["money"] -= theft_cost
                players[str(id)]["exp"] += 20
            else:
                embed = discord.Embed(color=discord.Colour.orange(), title='Тренинг прошел успешно!',
                                      description=f'Вы успешно прошли треннинг'
                                                  f' и готовы к новым приключениям на новом уровне!')
                await ctx.send(embed=embed)
                players[str(id)]["money"] -= theft_cost
                players[str(id)]["theft skill"] = to_theft_level_up
                players[str(id)]["exp"] += 20


    else:  # not authorized
        await not_authorized(ctx)


@bot.command(aliases=['steal'])
async def theft(ctx, target: str, victim: discord.Member):
    id = ctx.author.id

    if str(id) not in players.keys():
        await not_authorized(ctx)
        return

    if str(victim.status) != 'online':
        await custom_error(ctx, 'Пользователь не онлайн!')
        return

    if str(id) == str(victim.id):
        await custom_error(ctx, "Ключи потерял? Это ведь твой дом, его нельзя обворовывать!")
        return

    users.append(victim.id)

    wall = True
    for _ in range(10):
        if victim.id not in users:
            wall = False
            break
        await victim.send(f'{victim.mention}, включена сигнализация дома!'
                          f' Для вызова полиции напишите "{settings["prefix"]}police".')
        await asyncio.sleep(3)
    if wall:  # if not police arrived
        if target == 'money':
            c = round(players[str(victim.id)]["money"] * random.choice([0.3, 0.3, 0.3, 0.4, 0.4, 0.5, 0.6]), 1)
            embed = discord.Embed(color=discord.Colour.green(), title='Сигнализация отключена!',
                                  description=f'Вы успешно своровали {c}🪙')
            img = discord.File("source/img/robber.jpg", filename="robber.jpg")
            embed.set_image(url="attachment://robber.jpg")
            await ctx.send(embed=embed, file=img)

            players[str(id)]["money"] += c
            players[str(victim.id)]["money"] -= c
        else:
            victim_plants = [i for i in players[str(victim.id)]["buildings"].keys()]
            plant_1 = random.choice(victim_plants)
            plant_2 = random.choice(victim_plants)
            embed = discord.Embed(color=discord.Colour.green(), title='Сигнализация отключена!',
                                  description=f'Вы успешно своровали {plant_1} и {plant_2}!')
            img = discord.File("source/img/robber.jpg", filename="robber.jpg")
            embed.set_image(url="attachment://robber.jpg")
            await ctx.send(embed=embed, file=img)

            victim_lvl = players[str(victim.id)]["level"]

            # change income
            players[str(victim.id)]["income"] -= plants["levels"][str(victim_lvl)][plant_1]['power'] + \
                                                 plants["levels"][str(victim_lvl)][plant_2]['power']
            # del plants
            players[str(victim.id)]["buildings"][plant_1] -= 1
            players[str(victim.id)]["buildings"][plant_2] -= 1

            # if count of plants == 0, del from dict
            if players[str(victim.id)]["buildings"][plant_1] == 0:
                del players[str(victim.id)]["buildings"][plant_1]
            if players[str(victim.id)]["buildings"][plant_2] == 0:
                del players[str(victim.id)]["buildings"][plant_2]

            # add plant to user
            user_level = players[str(id)]["level"]
            players[str(id)]["income"] += plants["levels"][str(user_level)][plant_1]["power"] + \
                                          plants["levels"][str(user_level)][plant_2]["power"]

            if plant_1 in players[str(id)]["buildings"].keys():
                players[str(id)]["buildings"][plant_1] += 1
            else:
                players[str(id)]["buildings"][plant_1] = 1

            if plant_2 in players[str(id)]["buildings"].keys():
                players[str(id)]["buildings"][plant_2] += 1
            else:
                players[str(id)]["buildings"][plant_2] = 1

    else:
        if target == "money":
            chance = players[str(id)]["theft skill"] + 50 - players[str(victim.id)]["defence"]
            number = random.randint(0, 100)
            if 0 <= number <= chance <= 100 or chance >= 100:
                c = round(players[str(victim.id)]["money"] * random.choice([0.3, 0.4, 0.4, 0.5, 0.5, 0.6]), 1)
                embed = discord.Embed(color=discord.Colour.green(), title='Сигнализация включена...',
                                      description=f'...но вы оказались быстрее полиции и смогли своровать {c}🪙!')
                img = discord.File("source/img/robber.jpg", filename="robber.jpg")
                embed.set_image(url="attachment://robber.jpg")
                await ctx.send(embed=embed, file=img)
                players[str(id)]["money"] += c
                players[str(victim.id)]["money"] -= c
            else:
                c = round(players[str(id)]["money"] * 0.2, 1)
                embed = discord.Embed(color=discord.Colour.green(), title='Сигнализация включена...',
                                      description=f'...вы не смогли своровать и при побеге обронили {c}🪙, '
                                                  f'которые нашел хозяин дома!')
                img = discord.File("source/img/robber_fail.jpg", filename="robber_fail.jpg")
                embed.set_image(url="attachment://robber_fail.jpg")
                await ctx.send(embed=embed, file=img)
                players[str(id)]["money"] -= c
                players[str(victim.id)]["money"] += c
        else:
            c = round(players[str(victim.id)]["money"] * 0.2, 1)
            embed = discord.Embed(color=discord.Colour.green(), title='Сигнализация включена...',
                                  description=f'...вы не смогли своровать и при побеге обронили {c}🪙, '
                                              f'которые нашел хозяин дома!')
            img = discord.File("source/img/robber_fail.jpg", filename="robber_fail.jpg")
            embed.set_image(url="attachment://robber_fail.jpg")
            await ctx.send(embed=embed, file=img)
            players[str(id)]["money"] -= c
            players[str(victim.id)]["money"] += c
    players[str(id)]["exp"] += 20
    take_rep(id, 30)


@bot.command()
async def police(ctx):
    id = ctx.author.id

    if str(id) not in players.keys():
        await not_authorized(ctx)
        return

    if id not in users:
        await custom_error(ctx, "Ваш дом под охраной, нападения не было!")
        return
    del users[users.index(id)]

    await ctx.send('Сигнализация включена, полиция уже в пути!')


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(embed=discord.Embed(color=discord.Color.red(),
                                           title=f'Ошибка!', description=f'Команда не найдена, узнать о командах'
                                                                         f' можно испольхуя "{settings["prefix"]}help"'))
    elif "TimeoutError" in str(error):
        await ctx.send(embed=discord.Embed(color=discord.Color.red(), title=f'Ошибка!',
                                           description=f'Я не дождался от вас ответа...'))
    elif isinstance(error, commands.MissingRequiredArgument) or isinstance(error, commands.TooManyArguments):
        await ctx.send(embed=discord.Embed(color=discord.Color.red(), title=f'Ошибка!',
                                           description=f'Неправильные аргументы. Узнать о командах'
                                                       f' можно используя "{settings["prefix"]}help"'))
    else:
        await ctx.send(embed=discord.Embed(color=discord.Color.red(), title=f'Неизвестная ошибка!', description=error))


@bot.group(invoke_without_command=True)
async def help(ctx):
    embed = discord.Embed(color=discord.Colour.dark_purple(),
                          title='Help',
                          description=f'Используйте {settings["prefix"]}help <command> для получения расширенной информации.')
    embed.add_field(name="Игра", value="join_game\ndisconnect_game")
    embed.add_field(name="Казино", value="dice\nmoney")
    embed.add_field(name="Сад", value="plant\nmy_garden\n")
    embed.add_field(name="Общее", value="shop\ntheft\npolice")
    await ctx.send(embed=embed)


@help.command()
async def dice(ctx):
    embed = discord.Embed(color=discord.Colour.dark_purple(),
                          title='Dice', description='Позволяет играть с другими игроками в кости на монеты')
    embed.add_field(name="Syntax", value=f"{settings['prefix']}dice <amount> <member>")
    await ctx.send(embed=embed)


@help.command(aliases=['garden'])
async def my_garden(ctx):
    embed = discord.Embed(color=discord.Colour.dark_purple(),
                          title='Garden', description='Показывает статистику сада')
    embed.add_field(name="Syntax", value=f"{settings['prefix']}my_garden")
    embed.add_field(name="Aliases", value=f"{settings['prefix']}garden")
    await ctx.send(embed=embed)


@help.command(aliases=['steal'])
async def theft(ctx):
    embed = discord.Embed(color=discord.Colour.dark_purple(),
                          title='Theft',
                          description='Позволяет красть монеты или растения у других игроков. '
                                      'На успешность воровства влияет Уровень воровства и Уровень защиты.')
    embed.add_field(name="Syntax", value=f"{settings['prefix']}theft <target: money or plant> <member>")
    embed.add_field(name="Aliases", value=f"{settings['prefix']}steal")
    await ctx.send(embed=embed)


@help.command(aliases=['buy', 's'])
async def shop(ctx):
    embed = discord.Embed(color=discord.Colour.dark_purple(),
                          title='Shop', description='Открывает меню покупки.')
    embed.add_field(name="Syntax", value=f"{settings['prefix']}shop")
    embed.add_field(name="Aliases", value=f"{settings['prefix']}buy, {settings['prefix']}s")
    await ctx.send(embed=embed)


@help.command()
async def plant(ctx):
    embed = discord.Embed(color=discord.Colour.dark_purple(),
                          title='Plant', description='Открывает меню покупки растений.')
    embed.add_field(name="Syntax", value=f"{settings['prefix']}plant")
    await ctx.send(embed=embed)


@help.command(aliases=['moneys', 'coins', 'babki'])
async def money(ctx):
    embed = discord.Embed(color=discord.Colour.dark_purple(),
                          title='Money', description='Показывает количество монет.')
    embed.add_field(name="Syntax", value=f"{settings['prefix']}money")
    embed.add_field(name="Aliases",
                    value=f"{settings['prefix']}babki, "
                          f"{settings['prefix']}moneys, "
                          f"{settings['prefix']}coins")
    await ctx.send(embed=embed)


@help.command(aliases=['new_player'])
async def join_game(ctx):
    embed = discord.Embed(color=discord.Colour.dark_purple(),
                          title='Join_game', description='Позволяет присоединиться к игре.')
    embed.add_field(name="Syntax", value=f"{settings['prefix']}join_game")
    embed.add_field(name="Aliases", value=f"{settings['prefix']}new_player")
    await ctx.send(embed=embed)


@help.command()
async def disconnect_game(ctx):
    embed = discord.Embed(color=discord.Colour.dark_purple(),
                          title='Join_game', description='Позволяет выйти из игры (не обратимо).')
    embed.add_field(name="Syntax", value=f"{settings['prefix']}disconnect_game")
    await ctx.send(embed=embed)


@help.command()
async def police(ctx):
    embed = discord.Embed(color=discord.Colour.dark_purple(),
                          title='Police', description='Вызывает полицию, тем самым защищая вас от кражи.')
    embed.add_field(name="Syntax", value=f"{settings['prefix']}police")
    await ctx.send(embed=embed)


async def babki_babki_babki():
    iter = 0
    while babki_running:
        iter += 1
        if iter == 10:
            iter = 0
            save()

        for user in players.keys():
            if str(get(bot.get_all_members(), id=int(user)).status) == 'online':
                players[user]["money"] += players[user]["income"]
        await asyncio.sleep(1)


if __name__ == "__main__":
    bot.run(settings['TOKEN'])
