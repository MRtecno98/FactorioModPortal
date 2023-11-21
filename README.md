# Factorio Mod Portal

This script is a command line tool that downloads factorio mods 
from the official mod portal ~~**even with a non-paid account**~~ 
(only working for paid accounts currently, see <b>EDIT 2</b> in the announcement below).

## Announcement
~~As of issue #4 the api this script used has been restricted to paid accounts, so this project has now kinda lost~~
~~its original purpose.~~
~~With the recent new features it's still useful for people with paid accounts to download mods and dependencies automatically,~~
~~so i won't archive the repo yet. Any help in finding another similar workaround is welcome though, in that case please open~~
~~an issue or push a PR and i'll check it out.~~

#### EDIT 1: Sep 18 2022
~~As of commit [47737b8](https://github.com/MRtecno98/FactorioModPortal/commit/47737b8dce319d288b87a20c50a6a25b5e749d27) i have actually managed to workaround this problem using other mirrors provided by @radioegor146 
(at https://1488.me), thanks a lot :)~~

#### EDIT 2: Nov 21 2023
As of recent developments(see issue [#5](https://github.com/MRtecno98/FactorioModPortal/issues/5)) it seems like the other mirrors went down too, possibly because they fixed the googleapis endpoint that was added in commit 
[47737b8](https://github.com/MRtecno98/FactorioModPortal/commit/47737b8dce319d288b87a20c50a6a25b5e749d27)
(see previous update and issue #4 for details), until some other way to download the mods comes up this tool goes back to be only working for paid accounts.

## Warning
This project is OLD, it does work and I sporadically fix issues and bugs, but it has several design flaws and if I had the time I would probably rewrite it.
So don't expect too much from it.

## Usage
To execute the tool you need Python 3 installed, you can execute it in the command line using the python interpreter
