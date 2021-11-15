FROM python:3.8-buster

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update
RUN apt-get install jq -y

# CMD [ "/bin/bash", "aws --version" ]
# # CMD [ "bash", "./install_samcli.sh" ]