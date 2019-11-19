# remove server files
echo 'removing old dirs from server...'
rm -rf /Users/Hermann/Server/snorkel/kroll/pubmedutils
rm -rf /Users/Hermann/Server/snorkel/kroll/ksnorkel
rm -rf /Users/Hermann/Server/snorkel/kroll/preprocessing
rm -rf /Users/Hermann/Server/snorkel/kroll/pubtator
rm -rf /Users/Hermann/Server/snorkel/kroll/mesh
rm -rf /Users/Hermann/Server/snorkel/kroll/pytorch_gpu
rm -rf /Users/Hermann/Server/snorkel/kroll/graph
rm -rf /Users/Hermann/Server/snorkel/kroll/stories
rm -rf /Users/Hermann/Server/snorkel/kroll/narrative
rm -rf /Users/Hermann/Server/snorkel/kroll/umls


echo 'copying new files to server...'
cp -r pubmedutils /Users/Hermann/Server/snorkel/kroll/pubmedutils
cp -r ksnorkel /Users/Hermann/Server/snorkel/kroll/ksnorkel
cp -r preprocessing /Users/Hermann/Server/snorkel/kroll/preprocessing
cp -r pubtator /Users/Hermann/Server/snorkel/kroll/pubtator
cp -r mesh /Users/Hermann/Server/snorkel/kroll/mesh
cp -r pytorch_gpu /Users/Hermann/Server/snorkel/kroll/pytorch_gpu
cp -r graph /Users/Hermann/Server/snorkel/kroll/graph
cp -r stories /Users/Hermann/Server/snorkel/kroll/stories
cp -r narrative /Users/Hermann/Server/snorkel/kroll/narrative
cp -r umls /Users/Hermann/Server/snorkel/kroll/umls

cp requirements.txt /Users/Hermann/Server/snorkel/kroll/requirements.txt
cp clear_notebooks_output.sh /Users/Hermann/Server/snorkel/kroll/clear_notebooks_output.sh
echo 'finished'