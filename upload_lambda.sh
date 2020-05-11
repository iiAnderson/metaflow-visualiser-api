#!/bin/bash

if [ $# -ne 4 ]; then
    echo $0: usage: upload_lambda.sh zipname dirname bucket profile
    exit 1
fi

file=$1
bucket=$3
profile=$4

cd $2


virtualenv -q venv --python=python3 > /dev/null
source venv/bin/activate

mkdir dist
cp -rf src/* dist  > /dev/null
cp test_lambda.py dist
pip -q install -r src/requirements.txt -t dist/  > /dev/null
cd dist

# pytest test_lambda.py
# ret=$?
# if [ $ret -ne 0 ]; then
#     echo "Unit tests failed"
#     exit 1
# fi

rm test_lambda.py

zip -rq ../"$file" . 
cd ..
echo "Uploading to AWS S3 bucket"

aws s3 cp $file "s3://$bucket" --profile $profile

rm $file
rm -r dist

deactivate
rm -r venv

cd ..

echo "Uploaded $zipname to $bucket"
