eval "$(conda shell.bash hook)"
if [[ -z $1 ]]; then
    echo "Please input proper python env"
    exit 1
fi
conda activate $1