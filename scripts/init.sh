read -p "Enter project name: " PROJECT_NAME
read -p "Enter project description: " PROJECT_DESCRIPTION
read -p "Enter project project website: " PROJECT_WEBSITE
read -p "Enter minimum python version: " PYTHON_VERSION
read -p "Enter project author name: " AUTHOR_NAME
read -p "Enter project author email: " AUTHOR_EMAIL
read -p "Enter git project url: " GIT_URL
OLD_PROJECT_NAME="pytemplate"
rm -rf .git
echo $PWD
find . -not -path "./scripts/*" -type f -exec sed -i "s/$OLD_PROJECT_NAME/$PROJECT_NAME/g" {} \;
find . -not -path "./scripts/*" -type f -exec sed -i "s/AUTHOR_NAME/$AUTHOR_NAME/g" {} \;
find . -not -path "./scripts/*" -type f -exec sed -i "s/AUTHOR_EMAIL/$AUTHOR_EMAIL/g" {} \;
find . -not -path "./scripts/*" -type f -exec sed -i "s/PROJECT_DESCRIPTION/$PROJECT_DESCRIPTION/g" {} \;
find . -not -path "./scripts/*" -type f -exec sed -i "s/PYTHON_VERSION/$PYTHON_VERSION/g" {} \;
find . -not -path "./scripts/*" -type f -exec sed -i "s/PROJECT_WEBSITE/$PROJECT_WEBSITE/g" {} \;
mv src/$OLD_PROJECT_NAME src/$PROJECT_NAME
echo "# $PROJECT_NAME" > README.md
git init
git add .
git commit -m "initial commit"
git branch -M main
git remote add origin $GIT_URL
git push -u origin main
