from py_jama_rest_client.client import JamaClient
import sys, os

#  2025.6.29  Takahiro Takahahi @ASE

JAMA_URL           = (os.environ.get('JAMA_URL'))
# 認証情報は環境変数にある前提
CREDENTIALS        = (os.environ.get('JAMA_CLIENT_ID'), os.environ.get('JAMA_CLIENT_SECRET')) 

class BaselineMgr:
    def __init__(
        self,
        baseline_id : int, 
        dst_proj_id : int,
        dst_location_id : int
    ) -> None:

        self.baseline_id = baseline_id  # Baseline　IDを指定された情報で初期化
        self.dst_proj_id = dst_proj_id  # Copy先 Project　IDを指定された情報で初期化
        self.dst_location_id = dst_location_id  # Copy先 親アイテム　IDを指定された情報で初期化

        self.jama_client = JamaClient(JAMA_URL, credentials=CREDENTIALS, oauth=True,
                                 allowed_results_per_page=50)
                                 
        self.lst_baseline_items =[]  # Baselineに含まれる Itemのリスト

    def get_items(
        self
    ) -> None:

        # Baselineに含まれるitemを取得する
        self.lst_baseline_items = self.jama_client.get_baselines_versioneditems(self.baseline_id)

        print("Baselineに含まれるアイテム数:%d\n"% len(self.lst_baseline_items))

        return

    def post_items(
        self
    ) -> None:

        # 新しいIDマッピング: 元ID → 新ID
        id_map = {}
        counter = 0

        for item in self.lst_baseline_items:
            # 各アイテムの情報を取得
            item_type = item['itemType']
            fields = item['fields']
            old_id = item["id"]

            ###############################
            #  コピー先ロケーションの処理
            ###############################
            # コピーするitemの親IDを取得
            parent_info = item.get("baselineLocation", {}).get("parent", {})
            parent_ids = parent_info.get("item")

            if parent_ids: # 親IDが存在する場合
                parent_old_id = parent_ids[0]
                parent_new_id = id_map.get(parent_old_id)
                if parent_new_id is None:
                    raise Exception(f"親ID {parent_old_id} がまだ作成されていません")
                locationItem = {'item':parent_new_id}

            else: #　Baselineの中のルートアイテムをコピーする場合(親IDがいない)
                if self.dst_location_id != 0:
                    # Copy先の親アイテムIDが指定されている場合
                    dst_root_locationItem={'item':self.dst_location_id}  #親のID指定
                else:
                    dst_root_locationItem={'project':self.dst_proj_id}  #親のID指定
                locationItem = dst_root_locationItem

            itemTypeID=item_type
            dct_fields=fields

            # コピーできないフィールド値を削除
            del dct_fields['documentKey']
            del dct_fields['globalId']
            if "release" in dct_fields:
                del dct_fields['release']
            if "release1" in dct_fields:
                del dct_fields['release1']

            if "childItemType" in item:
                child_type_id = item['childItemType']
            else:
                child_type_id = 0

            # アイテムをコピー
            new_id = self.jama_client.post_item(project= self.dst_proj_id,item_type_id=itemTypeID, \
                                       child_item_type_id=child_type_id,\
                                       location=locationItem,fields=dct_fields)
            counter += 1
            print(f"\rデータを {counter} 件コピーしました", end='', flush=True) 
            # IDマップを更新
            id_map[old_id] = new_id            

        return

if __name__ == '__main__':
    args = sys.argv

    refresh = True
    if 4 != len(args):
            print("Usage:python baseline_cpy [baseline_id] [dst_proj_id] [dst_location_id]")
            sys.exit()

    baseline_id = (int)(args[1])
    dst_proj_id = (int)(args[2])
    dst_location_id = (int)(args[3])

    baline_mgr = BaselineMgr( baseline_id,dst_proj_id,dst_location_id)
    baline_mgr.get_items()
    baline_mgr.post_items()
    print(f"\nBaseline {baseline_id} のアイテムをプロジェクト {dst_proj_id} にコピーしました。")
