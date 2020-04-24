
## Lucene

### Installation

You need the following packages:

- subversion
- make
- g++
- JRE
- JDK

First, install [JCC](https://lucene.apache.org/pylucene/jcc/install.html):

    svn co https://svn.apache.org/repos/asf/lucene/pylucene/trunk/jcc jcc
    cd jcc
    python setup.py build
    python setup.py install

Next, download ANT and PyLucene:

    wget http://apache.lauf-forum.at//ant/binaries/apache-ant-1.9.14-bin.tar.gz
    tar -xvf apache-ant-1.9.14-bin.tar.gz
    
    wget http://apache.lauf-forum.at/lucene/pylucene/pylucene-8.1.1-src.tar.gz
    tar -xvf pylucene-8.1.1-src.tar.gz
    cd pylucene-8.1.1
    
Then, set the environment variable `JAVA_HOME` to the home of your Java installation (see `/usr/libexec/javahome`).

    export JAVA_HOME=...

Now, you need to modify the Makefile to add the correct environment variables:
    
- `ANT`: The `apache-ant-1.9.14/bin/ant` binary
- `PYTHON`: The value from `which python3`
- `JCC=$(PYTHON) -m jcc --shared`
- `NUM_FILES=10`

Then, run `make`.

    CC=CC make
    make install