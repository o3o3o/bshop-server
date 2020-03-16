# Intro

一个微信电商项目尝试

未完成的电商系统小程序后端(Django)， [前端实现](https://github.com/o3o3o/bshop-front)使用Uniapp

目前有已下功能:

* 简单的商家、用户系统
* API使用GraphQL
* 短信全使用twilio(yunpian)
* 微信充值、提现
* 后台管理界面


## Code Style

- linter: [flake8](http://flake8.pycqa.org/en/latest/)
- formatter: [black](https://github.com/python/black)

## Getting started

### Run with docker-compose
```
docker-compose build
docker-commpose up -d 
# Misc
docker-compose exec web bash
$> python manage.py createsuperuser
```

## Licence

MIT
