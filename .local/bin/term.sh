#!/bin/sh
# warpper script for suckless st, to show cowsay animals say your customize quotes from database
# define whcih animals to show
target_animal=$(shuf -e stegosaurus dragon milk turkey -n 1)

# run command
fortune ~/.local/share/fortune/database | expand | iconv -f utf-8 -t ascii//TRANSLIT | fold -s -w 60 | cowsay -n -f "$target_animal"

printf "\033]2;st\007"

# excute shell
exec zsh
