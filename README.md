# FlaskWebApplicationSample
EC2上で簡単な在庫管理システムを勉強用に開発

## アーキテクチャ

![Architecture](Architecture.png) 

WebサーバがAPサーバ、DBも兼ねる形。

ApacheがHTTPリクエストを受け取り、
WSGIを通してFlaskで記述したAPIを呼び出す。

そして、APIがDBを操作する。

## ファイル構成

- /var/www/html/v1

        api.py  
        api.wsgi

- /etc/httpd/conf

       httpd.conf
