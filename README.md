Using
=====

To use this plugin:

* build it:

        git clone git://github.com/RecursiveForest/morituri-whatcd.git
        cd morituri-whatcd
        python2 setup.py bdist_egg

* copy it to your plugin directory:

        mkdir -p $HOME/.morituri/plugins
        cp dist/morituri_*egg $HOME/.morituri/plugins

* verify that it gets recognized:

        rip cd rip --help

   You should see whatcd as a possible logger.

* use it:

        rip cd rip --logger=whatcd


Developers
==========

To use the plugin while developing uninstalled:

    python2 setup.py develop --install-dir=path/to/checkout/of/morituri
