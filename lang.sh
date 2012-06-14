
TRANS_DIR=translations
BABEL_CFG=$TRANS_DIR/babel.cfg
MSG_POT=$TRANS_DIR/messages.pot

case "$1" in
    init)
        if [ -f $MSG_POT ]
        then
            echo $"$MSG_POT already exists, run update instead"
            exit 1
        fi
        pybabel extract -F $BABEL_CFG -k lazy_gettext -o $MSG_POT .
        ;;
    new)

        if [ -n "$2" ]
        then
            echo $"Usage: $0 $1 {{langcode}}"
            exit 1
        fi

        LANG_DIR=$TRANS_DIR/$2

        if [ -d $LANG_DIR ]
        then
            echo $"$2 has already been created"
            exit 1
        fi

        pybabel init -i $MSG_POT -d $TRANS_DIR -l $2

        ;;
    compile)
        pybabel compile -d $TRANS_DIR
        ;;
    update)
        pybabel extract -F $BABEL_CFG -k lazy_gettext -o $MSG_POT .
        pybabel update -i $MSG_POT -d $TRANS_DIR
        ;;
    *)
        echo $"Usage: $0 {{init|new|translate|update}}"
        exit 1
esac

