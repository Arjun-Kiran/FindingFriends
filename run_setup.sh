echo "This script for setting up the developement enviroment for 'Finding Friends'"

BASEDIR=$(dirname $0)
VIRTUAL_ENV_CHAT_SERVER="${BASEDIR}/.venv/ChatServer/"
CHAT_SERVER_PATH="${BASEDIR}/chatserver/"

REQUIRMENT_FILE_CHAT_SERVER="${CHAT_SERVER_PATH}/requirements.txt"
VIRTUAL_ENV="${BASEDIR}/.venv/FindingFriend/"

echo "Script location: ${BASEDIR}"
echo "Python Virtual Environment: ${VIRTUAL_ENV}"
echo "Python Virtual Environment: ${VIRTUAL_ENV_CHAT_SERVER}"

if [ ! -d "${VIRTUAL_ENV}" ]
then
  echo "Can not find virtual enviroment, building virtual enviroment in path ${VIRTUAL_ENV}"
  python -m venv "${VIRTUAL_ENV}"
fi

if [ ! -d "${VIRTUAL_ENV_CHAT_SERVER}" ]
then
  echo "Can not find virtual enviroment, building virtual enviroment in path ${VIRTUAL_ENV_CHAT_SERVER}"
  python -m venv "${VIRTUAL_ENV_CHAT_SERVER}"
fi


source "${VIRTUAL_ENV}/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt


source "${VIRTUAL_ENV_CHAT_SERVER}/bin/activate"
pip install --upgrade pip
pip install -r "${REQUIRMENT_FILE_CHAT_SERVER}"
python ./chatserver/src/main.py