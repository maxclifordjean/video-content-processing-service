echo "prepare env..."
python3 -m venv vcp
source vcp/bin/activate
echo "env ok"

sh fs.sh
