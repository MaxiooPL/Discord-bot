import discord
import re
import os
import asyncio

TOKEN = ''
DANE_PLIK = 'phonebook.txt'

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True

client = discord.Client(intents=intents)

if not os.path.exists(DANE_PLIK):
    with open(DANE_PLIK, 'w', encoding='utf-8') as f:
        for _ in range(500):
            f.write('"", ""\n')


def wczytaj_dane():
    with open(DANE_PLIK, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f.readlines()]


def zapisz_dane(dane):
    # Posortuj dane według numeru lokalu
    def get_lokal_num(line):
        match = re.match(r'"(\d+)_\d",', line)
        return int(match.group(1)) if match else float('inf')

    dane = sorted([line for line in dane if line != '"", ""'], key=get_lokal_num)
    dane += ['"", ""'] * (500 - len(dane))  # Uzupełnij do 500 rekordów
    with open(DANE_PLIK, 'w', encoding='utf-8') as f:
        f.write('\n'.join(dane))


@client.event
async def on_ready():
    print(f'Zalogowano jako {client.user}')


@client.event
async def on_message(message):
    if message.author.bot:
        return

    try:
        if message.content == '!start':
            await message.channel.send("Bot działa! Podaj numer telefonu", delete_after=10)
            await message.delete()
            return

        if isinstance(message.channel, discord.TextChannel):
            user_nick = message.author.display_name
            match = re.match(r'^(\d{1,3})\s?\|', user_nick)

            if not match:
                msg = await message.channel.send(
                    "Nick musi zaczynać się od maks. 3 cyfr i znaku '|', np. '123 | TwojNick'.")
                await asyncio.sleep(10)
                await msg.delete()
                await message.delete()
                return

            lokal = match.group(1)
            telefon = message.content.strip()

            if not telefon.isdigit() or not (7 <= len(telefon) <= 10):
                msg = await message.channel.send("Numer telefonu musi zawierać od 7 do 10 cyfr.")
                await asyncio.sleep(10)
                await msg.delete()
                await message.delete()
                return

            dane = wczytaj_dane()
            istniejące_wpisy = [l for l in dane if l.startswith(f'"{lokal}_')]

            if len(istniejące_wpisy) >= 2:
                msg = await message.channel.send("Ten lokal ma już 2 numery. Czy chcesz zastąpić jeden? (tak/nie)",
                                                 delete_after=30)
                await message.delete()

                def check_response(m):
                    return m.author == message.author and m.channel == message.channel and m.content.lower() in ['tak',
                                                                                                                 'nie']

                try:
                    response = await client.wait_for('message', check=check_response, timeout=30.0)
                    await response.delete()
                    if response.content.lower() == 'tak':
                        msg = await message.channel.send("Który numer chcesz zastąpić? (1 lub 2)", delete_after=30)

                        def check_choice(m):
                            return m.author == message.author and m.channel == message.channel and m.content.strip() in [
                                '1', '2']

                        try:
                            choice = await client.wait_for('message', check=check_choice, timeout=30.0)
                            await choice.delete()
                            index_to_replace = int(choice.content.strip()) - 1
                            dane = [
                                f'"{lokal}_{index_to_replace + 1}", "{telefon}"' if line.startswith(
                                    f'"{lokal}_{index_to_replace + 1}"') else line
                                for line in dane
                            ]
                            zapisz_dane(dane)
                            conf = await message.channel.send(
                                f"Zmieniono numer dla lokalu {lokal}_{index_to_replace + 1}.", delete_after=10)
                        except asyncio.TimeoutError:
                            await message.channel.send("Czas minął. Nie zmieniono numeru.", delete_after=10)
                    else:
                        await message.channel.send("Anulowano operację.", delete_after=10)
                except asyncio.TimeoutError:
                    await message.channel.send("Czas minął. Nie zmieniono numeru.", delete_after=10)
                return

            # Nowy wpis
            for i, linia in enumerate(dane):
                if linia == '"", ""':
                    suffix = "_1" if not istniejące_wpisy else "_2"
                    dane[i] = f'"{lokal}{suffix}", "{telefon}"'
                    zapisz_dane(dane)
                    msg = await message.channel.send(f"Zarejestrowano numer {telefon} dla lokalu {lokal}{suffix}.",
                                                     delete_after=10)
                    await message.delete()
                    return

            await message.channel.send("Brak wolnych miejsc w bazie danych.", delete_after=10)
            await message.delete()

    except Exception as e:
        print(f"Błąd: {e}")


client.run(TOKEN)
