# baseline_cpy
Jama Script
Copy a Jama baseline into another project

## Condition
py_jama_rest_client が必要です (pip install py_jama_rest_client)<br>
以下の環境変数を設定してから実行してください<br>
JAMA_URL<br>
JAMA_CLIENT_SECRET<br>
JAMA_CLIENT_ID<br>

## Usage
python baseline_cpy [baseline_id] [dst_proj_id] [dst_location_id]<br>
baseline_id : コピーするbaselineのID<br>
dst_proj_id : コピー先のProject ID<br>
dst_location_id : コピー先のアイテムID（Projectルートにコピーする場合は０を指定する事）<br>

