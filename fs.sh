echo "create directory for video storage..."
echo "\n"
mkdir /tmp/video-storage
mkdir /tmp/video-storage/dash
mkdir /tmp/video-storage/hls
ln -s /tmp/video-storage .
echo "Done"
