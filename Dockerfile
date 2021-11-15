FROM python:3.8-buster

# ADD CiscoUmbrellaRootCA.Pem /usr/src/app/CiscoUmbrellaRootCA.pem
# ADD CiscoUmbrellaRootCA.Pem /etc/ssl/certs/CiscoUmbrellaRootCA.pem
# RUN chmod 644 /usr/src/app/CiscoUmbrellaRootCA.pem /etc/ssl/certs/CiscoUmbrellaRootCA.pem && \
#     update-ca-certificates;cat /usr/src/app/CiscoUmbrellaRootCA.pem >> /usr/local/lib/python3.8/site-packages/pip/_vendor/certifi/cacert.pem

# WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update
RUN apt-get install jq -y

# COPY . .

CMD [ "/bin/bash", "aws --version" ]
# CMD [ "bash", "./install_samcli.sh" ]