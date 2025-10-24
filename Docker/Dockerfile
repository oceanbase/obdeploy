FROM registry.openanolis.cn/openanolis/anolisos:8.9
ENV PATH="/opt/miniconda/bin:$PATH"
ENV TZ=UTC-8
ENV CRYPTOGRAPHY_OPENSSL_NO_LEGACY=1

ADD Docker/ob_build /usr/bin/
ADD Docker/python-env-activate.sh /usr/bin/py-env-activate

RUN yum install -y wget  \
    && wget -O /etc/yum.repos.d/epel.repo http://mirrors.aliyun.com/repo/epel-7.repo \
    && yum -y install libffi-devel bzip2-devel readline readline-devel jq which bison ncurses-devel libaio autoconf automake libtool perl-CPAN gettext-devel perl-devel openssl-devel zlib-devel curl-devel  xz-devel \
        expat-devel asciidoc xmlto rpm-build cmake make gcc gcc-c++ python2-devel python3-devel sudo git mysql-devel \
    && yum clean all

RUN wget https://repo.anaconda.com/miniconda/Miniconda2-py27_4.8.3-Linux-x86_64.sh --no-check-certificate\
    && bash Miniconda2-py27_4.8.3-Linux-x86_64.sh -p /opt/miniconda -b \
    && rm -rf Miniconda2-py27_4.8.3-Linux-x86_64.sh \
    && conda clean --all -y

COPY requirements3.txt /workspaces/obd/requirements3.txt
COPY service/service-requirements.txt   workspaces/obd/service-requirements.txt

RUN conda create -n py27 -y python=2.7 \
    && source /opt/miniconda/bin/activate base \
    && pip config set global.index-url https://mirrors.aliyun.com/pypi/simple \
    && pip config set global.trusted-host  mirrors.aliyun.com \
    && pip install pyinstaller==3.6 \
    && rm -rf ~/.cache/pip \
    && conda clean -a -y

RUN conda create -n py311 -y python=3.11 \
    && source /opt/miniconda/bin/activate py311 \
    && pip config set global.index-url https://mirrors.aliyun.com/pypi/simple \
    && pip config set global.trusted-host  mirrors.aliyun.com \
    && pip install -r /workspaces/obd/requirements3.txt \
    && pip install -r /workspaces/obd/service-requirements.txt \
    && pip install pyinstaller==3.6 \
    && pip cache purge \
    && echo "source /opt/miniconda/bin/activate py11" >> ~/.bashrc \
    && /opt/miniconda/bin/conda clean -a -y \
    && rm -rf /workspaces/obd

# install nodejs and yarn
RUN wget https://rpm.nodesource.com/setup_20.x  \
    && touch /etc/redhat-release \
    && bash  setup_20.x \
    && rm -f  /etc/redhat-release \
    && yum install -y nodejs \
    && yum clean all

RUN npm install -g yarn \
    && yarn config delete registry --global \
    && yarn config set registry https://registry.npmmirror.com/  --global \
    && npm cache clean --force