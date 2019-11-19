mkdir notebooks_without_output
cd notebooks_without_output

rm *.ipynb
cp ../*.ipynb .

jupyter nbconvert --ClearOutputPreprocessor.enabled=True --inplace *.ipynb