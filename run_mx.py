import subprocess
import os
import pathlib
import shutil
import tomllib


filepath = pathlib.Path(__file__).absolute()

CUBEMX_FOLDER_PATH = filepath.parent

for parent in CUBEMX_FOLDER_PATH.parents:
    if parent.name == "lib":
        PROJECTPATH = parent.parent
        PROJECTNAME = PROJECTPATH.stem
        break
else:
    PROJECTPATH = CUBEMX_FOLDER_PATH
    PROJECTNAME = "cubemxgen"


CFGPATH = CUBEMX_FOLDER_PATH / "config.toml"
IOC_PATH = CUBEMX_FOLDER_PATH / f"{PROJECTNAME}.ioc"


TEMPFOLDER = CUBEMX_FOLDER_PATH / "temp"
AUTOGENFOLDER = TEMPFOLDER / PROJECTNAME
SU_LOC = CUBEMX_FOLDER_PATH / "StartupScript.txt"

BACKUPFOLDER = CUBEMX_FOLDER_PATH / "backup"


dir_mapping = {("src", "Src"), ("include", "Inc")}


BOARDNAME_KEY = "BOARDNAME"
MCUNAME_KEY = "MCUNAME"
CUBEMX_LOC_KEY = "CUBEMX_LOC"


def create_temp_folder():
    try:
        os.mkdir(TEMPFOLDER)
    except:
        print("TEMPFOLDER not cleaned up")
        return


def create_backup_folder():
    try:
        BACKUPFOLDER.mkdir(parents=True, exist_ok=True)
    except:
        print("TEMPFOLDER not cleaned up")
        return


def remove_temp_folder():
    try:
        shutil.rmtree(TEMPFOLDER)
    except:
        print("TEMPFOLDER not cleaned up")
        return


def createdefaultcfgfile(path):
    with open(path, "w") as f:
        f.write(
            f"""# Config for the python script to generate CUBE MX files

# Specify BOARDNAME example "NUCLEO-F072RB" otherwise
# generate ioc file with CubeMX and save it in this folder
{BOARDNAME_KEY} = ""

# Specify the folder in which the cubemx application is located, usually:
# "C:/Program Files/STMicroelectronics/STM32Cube/STM32CubeMX"
{CUBEMX_LOC_KEY} = ""                
"""
        )


def copy_files(src, dest):
    try:
        shutil.move(src, dest)
    except Exception as e:
        print(e)


def run_mx(
    cwd,
    script_s=None,
    headless=False,
):
    if script_s is not None:
        with open(SU_LOC, "w") as file:
            file.write(script_s)

    cmd = [
        "jre\\bin\\java.exe",
        "-jar",
        "STM32CubeMX.exe",
        "-s" if not headless else "-q",
        str(SU_LOC) if script_s is not None else "",
    ]
    with subprocess.Popen(
        args=cmd,
        shell=True,
        stdout=subprocess.PIPE,
        cwd=cwd,
        text=True,
        universal_newlines=True,
    ) as proc:
        while proc.poll() is None:
            if proc.stdout.readable():
                output = proc.stdout.readline().strip()

                if "[ERROR]" in output:
                    break

    if script_s is not None:
        os.remove(SU_LOC)


def load_cfg():
    if not CFGPATH.exists():
        print("config.toml not found, creating default!")
        createdefaultcfgfile(CFGPATH)
        exit(1)

    with open(CFGPATH, "rb") as f:
        cfg = tomllib.load(f)

    if not any(value.strip() != "" for value in cfg.values()):
        print("config.toml is empty!")
        createdefaultcfgfile(CFGPATH)
        exit(1)

    return cfg


def read_cubemx_loc(cfg: dict[str, str]):
    if not CUBEMX_LOC_KEY in cfg or (CUBEMX_LOC := cfg[CUBEMX_LOC_KEY]) == "":
        print(f"{CUBEMX_LOC_KEY} not specified in config.toml")
        return

    CUBEMX_PATH = pathlib.Path(CUBEMX_LOC)

    if CUBEMX_PATH.is_file():
        CUBEMX_PATH = CUBEMX_PATH.parent

    if not CUBEMX_PATH.exists():
        print(f"Invalid Path entered for {CUBEMX_LOC_KEY}")
        return

    if not (CUBEMX_PATH / "STM32CubeMX.exe").exists():
        print(
            f"""Cube Mx was not found in specified location:
{CUBEMX_LOC_KEY} = "{CUBEMX_PATH.as_posix()}" """
        )
        return

    return CUBEMX_PATH





def open_ioc(
    load_cmd,
    
    cubemx_path,
    post_cmd="",
):
    script = f"""
{load_cmd}
SetStructure Basic
SetCopyLibrary "copy as reference"

project name {PROJECTNAME}
project path "{TEMPFOLDER}"
project toolchain Makefile
project couplefilesbyip 1
{post_cmd}
""".replace(
        "c:\\", "C:\\"
    )

    create_temp_folder()

    for normal, temp in dir_mapping:
        copy_files(CUBEMX_FOLDER_PATH / normal, AUTOGENFOLDER / temp)

    try:
        run_mx(cubemx_path, script_s=script, headless=False)
    except Exception as e:
        print(e)
    except KeyboardInterrupt as e:
        print("Interrupted!")

    for normal, temp in dir_mapping:
        copy_files(AUTOGENFOLDER / temp, CUBEMX_FOLDER_PATH / normal)

    remove_temp_folder()


def main():
    cfg = load_cfg()
    cube_loc = read_cubemx_loc(cfg)

    ioc_path = None
    if IOC_PATH.exists():
        ioc_path = IOC_PATH
    else:
        for item in CUBEMX_FOLDER_PATH.glob("*.ioc"):
            ioc_path = item
    
    post_cmd = ""
    load_cmd = ""

    if ioc_path is not None and ioc_path.exists():
        load_cmd = f'config load "{ioc_path}"'
    else:
        if BOARDNAME_KEY in cfg and (board_name := cfg[BOARDNAME_KEY]) != "":
            load_cmd = f"loadboard {board_name} allmodes"
            post_cmd = f'config saveext "{CUBEMX_FOLDER_PATH/PROJECTNAME}.ioc" '


    open_ioc(load_cmd, cube_loc, post_cmd)


if __name__ == "__main__":
    main()
