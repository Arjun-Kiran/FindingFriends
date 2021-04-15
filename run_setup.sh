echo "This script for setting up the developement enviroment for 'Finding Friends'"

BASEDIR=$(dirname $0)
VIRTUAL_ENV="${BASEDIR}/.venv/FindingFriend/"

echo "Script location: ${BASEDIR}"
echo "Python Virtual Environment: ${VIRTUAL_ENV}"

if [ ! -d "${VIRTUAL_ENV}" ]
then
  echo "Can not find virtual enviroment, building virtual enviroment in path ${VIRTUAL_ENV}"
  python -m venv "${VIRTUAL_ENV}"
fi

source "${VIRTUAL_ENV}/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt