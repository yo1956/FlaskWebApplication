import sys
sys.path.append("/usr/local/lib/python3.8/site-packages")
sys.path.append("/usr/local/lib64/python3.8/site-packages")
from flask import Flask, jsonify, request
import json
from flaskext.mysql import MySQL

app = Flask(__name__)
mysql = MySQL()

#---------------------------------------------------------#
#                         DB関連                           #
#---------------------------------------------------------#
app.config['MYSQL_DATABASE_USER'] = 'connect_user@localhost'
app.config['MYSQL_DATABASE_PASSWORD'] = 'pass'
app.config['MYSQL_DATABASE_DB'] = 'aws_test'
app.config['MYSQL_DATABASE_HOST'] = '127.0.0.1'
app.config['MYSQL_DATABASE_PORT'] = 3306

mysql.init_app(app)

# SQL発行(SELECT用)
def ExecuteQuery(sql):
  cur = mysql.connect().cursor()
  cur.execute(sql)
  results = [dict((cur.description[i][0], value)
    for i, value in enumerate(row)) for row in cur.fetchall()]
  return results

# SQL発行(INSERT, UPDATE, DELETE用)
def ExecuteUpdateQuery(sql):
  con = mysql.connect()
  cur = con.cursor()
  cur.execute(sql)
  results = [dict((cur.description[i][0], value)
    for i, value in enumerate(row)) for row in cur.fetchall()]
  con.commit()
  return results

@app.route('/', methods=['get'])
def index():
    return 'AWS'

#---------------------------------------------------------#
#                   簡単な在庫管理システム                    #
#---------------------------------------------------------#
#                        API関数                           #
#          急いで書き殴ったものなのでリファクタしたい...         #
#---------------------------------------------------------#
#----------------------------------------
# (1) 在庫の更新、作成
#----------------------------------------
# POST /v1/stocks
@app.route('/stocks', methods=['post'])
def create_or_update_stock():
    request_data = request.get_json()

    str_json = json.dumps(request_data) # json.loadsはjson形式の文字列でないと辞書に変換できないため前準備
    dic_data = json.loads(str_json)     # 一度辞書型にしておく
    isExistAmount = True
    if dic_data.get('amount') == None:
        isExistAmount = False


    # amountの指定がない場合は1としておく
    if isExistAmount == False:
        dic_data = { 'name': dic_data['name'], 'amount': 1}
    # amountの指定があるなら異常系チェック
    else:
        # amountの値が整数でない場合はエラー
        if not isinstance(dic_data['amount'], int):
            return jsonify({"message": "ERROR"})

        # amountの値が正数でない場合はエラー
        if dic_data['amount'] <= 0:
            return jsonify({"message": "ERROR"})

    sql_name   = dic_data['name']
    sql_amount = int(dic_data['amount'])

    # すでに存在する品物についてはamountを増やす
    # まだ在庫として存在しないものの追加は、レコードごと増やす
    amount_db = ExecuteQuery("select AMOUNT from PRODUCTS where NAME = '" + sql_name + "'")
    if len(amount_db) == 0: # amount_dbが取れてないということはレコード無し
        exec = ExecuteUpdateQuery("insert into PRODUCTS (name, amount) values( '" + sql_name +"', " + str(sql_amount) + " )")
    else:
        sql_amount += int(amount_db[0].get('AMOUNT'))
        exec = ExecuteUpdateQuery("update PRODUCTS set AMOUNT = " + str(sql_amount) + " where NAME = '" + sql_name + "'")

    return request_data

#----------------------------------------
# (2) 在庫チェック
#----------------------------------------
# GET /v1/stocks/<string:name>
@app.route('/stocks/<string:name>')
def get_stock(name):
    ret = ExecuteQuery("select * from PRODUCTS where NAME = '" + name + "'")
    str_ret += '{"' + ret.get('NAME') + '":' + str(ret.get('AMOUNT')) + '}'
    return str_ret

# GET /v1/stocks
@app.route('/stocks')
def get_all_stocks():
  ret = ExecuteQuery('select * from PRODUCTS where AMOUNT > 0')
  str_ret = '{'
  for i in ret:
      str_ret += '"' + i.get('NAME') + '":' + str(i.get('AMOUNT')) + ','
  return str_ret[:-1] + '}'

#----------------------------------------
# (3) 販売
#----------------------------------------
# POST /v1/sales
@app.route('/sales', methods=['post'])
def sell():
    request_data = request.get_json()

    str_json = json.dumps(request_data) # json.loadsはjson形式の文字列でないと辞書に変換できないため前準備
    dic_data = json.loads(str_json)     # 一度辞書型にしておく
    isExistAmount = True
    if dic_data.get('amount') == None:
        isExistAmount = False
    isExistPrice = True
    if dic_data.get('price') == None:
        isExistPrice = False

    # amountの指定がない場合は1としておく
    if isExistAmount == False:
        if isExistPrice:
            dic_data = { 'name': dic_data['name'], 'amount': 1, 'price':dic_data['price']}
        else:
            dic_data = { 'name': dic_data['name'], 'amount': 1 }
    # amountの指定があるなら異常系チェック
    else:
        # amountの値が整数でない場合はエラー
        if not isinstance(dic_data['amount'], int):
            return jsonify({"message": "ERROR"})

        # amountの値が正数でない場合はエラー
        if dic_data['amount'] <= 0:
            return jsonify({"message": "ERROR"})

    sql_name   = dic_data['name']
    sql_amount = int(dic_data['amount'])

    # 在庫に存在する品物についてはamountを減らす(ただし在庫数を超える数の販売要求は、在庫数分の販売とする)
    # 在庫に存在しないものの販売要求は、エラーとした
    amount_db = ExecuteQuery("select AMOUNT from PRODUCTS where NAME = '" + sql_name + "'")
    if len(amount_db) == 0: # amount_dbが取れてないということはレコード無し
        return jsonify({"message": "ERROR"})
    else:
        update_amount = int(amount_db[0].get('AMOUNT')) - sql_amount
        if update_amount < 0:
            update_amount = 0
        exec = ExecuteUpdateQuery("update PRODUCTS set AMOUNT = " + str(update_amount) + " where NAME = '" + sql_name + "'")
    
    # priceの指定がある場合は売上に加算
    if isExistPrice:
        sql_price = int(dic_data['price'])

        # priceの値が正数でない場合はエラーとする
        if sql_price <= 0:
            return jsonify({"message": "ERROR"})

        earnings = sql_amount * sql_price
        exec = ExecuteUpdateQuery("insert into SALES (name, earnings) values( '" + sql_name +"', " + str(earnings) + " )")

    return request_data

#----------------------------------------
# (4) 売り上げチェック
#----------------------------------------
# GET /v1/stocks
@app.route('/sales', methods=['get'])
def get_sales():
  # formatは小数点の表示調整用、replaceは数値のカンマ除去
  exec = ExecuteQuery("select replace(format(ceiling(sum(EARNINGS) * 10)/10, 1), ',', '') as sales from SALES")
  ret = '{"sales": ' + exec[0].get('sales') + '}'
  return ret

#----------------------------------------
# (5) 全削除
#----------------------------------------
# DELETE /v1/stocks
@app.route('/stocks', methods=['delete'])
def delete_all():
  ret = ExecuteUpdateQuery('delete from PRODUCTS')
  ret = ExecuteUpdateQuery('delete from SALES')
  return ''