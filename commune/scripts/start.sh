#

# if commune does not exist build it

# if docker is not running, start it

CONTAINER_NAME=commune
START_PORT=50050
END_PORT=50250
GPUS=null
if  "$1" == "--port-range" ; then
  # add the port range flag by taking the next two arguments
  # if '-' in the second argument, split it and set the start and end ports
    START_PORT=$2
    END_PORT=$3
    PORT_RANGE=$START_PORT-$END_PORT
    echo "Setting port range to $PORT_RANGE"
fi

PORT_RANGE=$START_PORT-$END_PORT

if [ "$BUILD" == true ]; then
  docker build -t commune .
fi

CONTAINER_EXISTS=$(docker ps -q -f name=$CONTAINER_NAME)  
CONTAINER_ID=$(docker ps -aqf "name=$CONTAINER_NAME")
if [ $CONTAINER_EXISTS ]; then
  echo "Stopping and removing existing container $CONTAINER_NAME ID=$CONTAINER_ID"
  docker stop $CONTAINER_NAME
fi

if [ $CONTAINER_ID ]; then
  echo "Removing existing container $CONTAINER_NAME ID=$CONTAINER_ID"
  docker rm $CONTAINER_ID
fi

CMD_STR="docker run -d --name $CONTAINER_NAME --shm-size 4gb \
  -v ~/.$CONTAINER_NAME:/root/.$CONTAINER_NAME \
  -v $PWD:/app \
  -p $PORT_RANGE:$PORT_RANGE \
  --restart unless-stopped \
  $CONTAINER_NAME"

if [ $GPUS != 'null' ]; then
  CMD_STR="$CMD_STR --gpus $GPUS"
fi

echo "Starting container with command: $CMD_STR"
eval $CMD_STR

# run c set_port_range to set the port range
# run c set_port_range 50050-50250

echo "Setting port range to $PORT_RANGE"
docker exec commune bash -c "c set_port_range $PORT_RANGE"


# scan for open port ranges of 100

# if [ "$1" == "--c" ] || [ "$1" == "-s" ]; then
#   echo "Scanning for open port ranges of 100"
#   for i in {50000..50250..100}; do
