#!/bin/sh
# remember to enable it with your init
inotifywait -m -e create,move "$HOME" --format "%f" | while read NAME; do
    case "$NAME" in
        "Downloads"|".SoulseekQt"|"whatever directories or files auto generated and you don't want it")
            rm -rf "$HOME/$NAME"
            ;;
    esac
done
