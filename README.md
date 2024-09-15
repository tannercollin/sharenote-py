# sharenote-py

A self-hosted alternative backend for the Obsidian [Share Note](https://github.com/alangrainger/share-note) plugin.

## Description

This re-implements the [share-note-self-hosted-backend](https://github.com/alangrainger/share-note-self-hosted-backend) in Python with a few changes:
- fully documented setup instructions
- no database
- readable links in the form of `https://notes.example.com/my-test-note-d731f1`
- note encryption is not yet implemented (I trust my own server)
- note expiry is not yet implemented

## Setup

1. Point a domain / subdomain to your server.
2. Set up sharenote-py using the instructions below.
3. Install the "Share Note" community plugin by Alan Grainger.
4. Activate the plugin, open the plugin's settings page.
5. Disable "Share as encrypted by default" at the bottom (not yet implemented), close settings.
6. Edit the `.obsidian/plugins/share-note/data.json` file in your vault's filesystem.
7. Set the "server" value to your server's URL from step 1, example: `https://notes.example.com` (no trailing slash).
8. Open Obsidian's Community Plugins settings, then deactivate and reactivate the Share Note plugin.


## Python-based Installation

This guide assumes a modern Debian or Ubuntu GNU/Linux server.

Install dependencies:
```text
$ sudo apt install python3 python3-pip python3-virtualenv
```

Clone this repo, create a venv, activate it, and install:
```text
$ git clone https://github.com/tannercollin/sharenote-py.git
$ cd sharenote-py/
$ virtualenv -p python3 env
$ source env/bin/activate
(env) $ pip install -r requirements.txt
```

Copy the settings file and edit it:
```text
$ cp settings.py.example settings.py
$ sensible-editor settings.py
```

You can now run it directly:
```text
$ source env/bin/activate
(env) $ python main.py
```

### Python Process Control

You can keep sharenote-py alive with [supervisor](https://pypi.org/project/supervisor/):

```text
$ sudo apt install supervisor
$ sudo touch /etc/supervisor/conf.d/sharenote.conf
$ sudoedit /etc/supervisor/conf.d/sharenote.conf
```

Edit the file, replacing your user and sharenote-py location:

```text
[program:sharenote]
user=tanner
directory=/home/tanner/sharenote-py
command=/home/tanner/sharenote-py/env/bin/python -u main.py
autostart=true
autorestart=true
stderr_logfile=/var/log/sharenote.log
stderr_logfile_maxbytes=10MB
stdout_logfile=/var/log/sharenote.log
stdout_logfile_maxbytes=10MB
```

Next configure a reverse proxy following the instructions below.

## Reverse proxy

To expose sharenote-py via https, you should configure an nginx reverse proxy:

```text
$ sudo apt install nginx certbot python3-certbot-nginx
$ sudoedit /etc/nginx/sites-available/default
```

Add to the bottom of the file:

```text
server {
    root /var/www/html;
    index index.html index.htm;

    server_name notes.example.com;  # replace with the domain you pointed to the server. don't forget the semicolon.

    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:8086/;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

	# will get switched automatically:
	listen 80;
}
```

Then run `sudo certbot --nginx` and follow the prompts.

Generate SSL certificate:

```text
$ sudo service nginx restart
$ sudo certbot --nginx
```

Follow prompts to activate HTTPS and enable redirects.

## License

This program is free and open-source software licensed under the MIT License. Please see the `LICENSE` file for details.

That means you have the right to study, change, and distribute the software and source code to anyone and for any purpose. You deserve these rights.

## Acknowledgements

Thanks to [@alangrainger] (https://www.github.com/alangrainger) for making the Share Note plugin.

Thanks to all the devs behind Obsidian.

