## Daftar

![GitHub repo status](https://img.shields.io/badge/status-active-green?style=flat)
![GitHub license](https://img.shields.io/github/license/sheikhartin/daftar)
![GitHub contributors](https://img.shields.io/github/contributors/sheikhartin/daftar)
![GitHub tag (latest by date)](https://img.shields.io/github/v/tag/sheikhartin/daftar)
![GitHub repo size](https://img.shields.io/github/repo-size/sheikhartin/daftar)

The word Daftar comes from Farsi (دفتر), which means notebook. This website is implemented with the Django framework and allows you to post in Markdown format and also has a commenting service inside!

### How to Use

First, install the dependencies:

```bash
poetry install
```

Configure the database and adapt the environment variables to it... Look at the example [here](daftar/.env.example).

Apply migrations:

```bash
poetry run python manage.py makemigrations \
&& poetry run python manage.py migrate
```

Test it before running:

```bash
poetry run python manage.py test
```

Run it:

```bash
poetry run python manage.py runserver --insecure
```

Check project status for deployment:

```bash
poetry run python manage.py check --deploy
```

**Note**: Only superusers can update posts and comments through the website...

### License

This project is licensed under the MIT license found in the [LICENSE](LICENSE) file in the root directory of this repository.
