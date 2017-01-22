FROM ubuntu:16.04

# install pip
RUN apt-get update
RUN apt-get -y install python-pip python-dev build-essential
RUN pip install --upgrade pip

# delete this
RUN pip install scipy
RUN pip install tensorflow

# special dependency for scipy image utils
RUN pip install Pillow

# copy repo over
COPY . repo

# install requirements
RUN pip install -r repo/requirements.txt

CMD repo/train-dcgan.py --dataset repo/data/MS-Celeb-1M-P1/aligned/ --epoch 1
# ENTRYPOINT ["repo/train-dcgan.py"]
# CMD ["--dataset repo/data/MS-Celeb-1M-P1/aligned/ --epoch 1"]
