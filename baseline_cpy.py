
from py_jama_rest_client.client import JamaClient
import sys, os

#  Ver 1.0 2025.6.29  Takahiro Takahahi @ASE
#  Ver 2.0 2025.8.21  Supports top of tree completion
#  Ver 3.0 2025.8.29  Supports setting relationships

JAMA_URL           = (os.environ.get('JAMA_URL'))
# 認証情報は環境変数にある前提
CREDENTIALS        = (os.environ.get('JAMA_CLIENT_ID'), os.environ.get('JAMA_CLIENT_SECRET')) 
USER_PASS          = (os.environ.get('JAMA_USER'), os.environ.get('JAMA_PASS'))
OAUTH_LOGIN        = False

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

        if OAUTH_LOGIN:
            self.jama_client = JamaClient(JAMA_URL, credentials=CREDENTIALS, oauth=True,
                                    allowed_results_per_page=50)
        else:
            self.jama_client = JamaClient(JAMA_URL, credentials=USER_PASS,  oauth=False,
                                          allowed_results_per_page=50)
            
        self.lst_baseline_items =[]  # Baselineに含まれる Itemのリスト

    def get_items(
        self
    ) -> None:

        # Baselineに含まれるitemを取得する
        self.lst_baseline_items = self.jama_client.get_baselines_versioneditems(self.baseline_id)

        print("Baselineに含まれるアイテム数:%d\n"% len(self.lst_baseline_items))

        return

    def set_relationships(
        self
    ) -> None:

        for old_id in self.id_map.keys():
            try:
                lst_relation=self.jama_client.get_baselines_versioneditems_versionedrelationships(self.baseline_id,old_id)
            except Exception as e:
                if "Resource not found. " not in str(e):
                    print(f"Error fetching relationships for origin id {old_id}: {e}")
            else:
                for rel in lst_relation:
                    source_old_id = rel.get("fromItem", 0)
                    target_old_id = rel.get("toItem", 0)
                    relationshipType = rel["relationshipType"][0]
                    source_new_id = self.id_map.get(source_old_id[0],None)
                    target_new_id = self.id_map.get(target_old_id[0],None)
                    if source_new_id and target_new_id:
                        # 関係を設定
                        try:
                            ret = self.jama_client.post_relationship(from_item=source_new_id, to_item=target_new_id, relationship_type=relationshipType)
                        except Exception as e:
                            pass
                        else:
                            if ret:
                                print(f"Relationship set: {source_new_id} -> {target_new_id}")
        
        return            
    def post_items(
        self
    ) -> None:

        # 新しいIDマッピング: 元ID → 新ID
        self.id_map = {}
        counter = 0

        # Baseline内のアイテムID→アイテム情報の辞書を作成
        baseline_item_dict = {item['id']: item for item in self.lst_baseline_items}

        # sequenceでソート（親→子の順）
        sorted_items = sorted(self.lst_baseline_items, key=lambda x: x['baselineLocation']['sequence'])

        def ensure_parent_created(parent_old_id):
            # すでに作成済みならID返す
            if parent_old_id in self.id_map:
                return self.id_map[parent_old_id]
            # Baseline内に親があればそちらを優先
            parent_baseline_item = baseline_item_dict.get(parent_old_id)
            if parent_baseline_item:
                # sequence順で先に作成されているはず
                return self.id_map.get(parent_old_id)
            # Baselineに親がなければget_itemで最新Ver取得
            parent_item = self.jama_client.get_item(parent_old_id)
            parent_type = parent_item['itemType']
            parent_fields = parent_item['fields']
            parent_info2 = parent_item.get("location", {}).get("parent", {})
            # location決定
            if "item" in parent_info2:
                grand_parent_old_id = parent_info2["item"]
                grand_parent_new_id = ensure_parent_created(grand_parent_old_id)
                locationItem = {'item': grand_parent_new_id}
            elif "project" in parent_info2:
                if self.dst_location_id != 0:
                    locationItem = {'item': self.dst_location_id}
                else:
                    locationItem = {'project': self.dst_proj_id}
            else:
                if self.dst_location_id != 0:
                    locationItem = {'item': self.dst_location_id}
                else:
                    locationItem = {'project': self.dst_proj_id}

            for k in ['documentKey', 'globalId', 'release', 'release1']:
                if k in parent_fields:
                    del parent_fields[k]
            child_type_id = parent_item.get('childItemType', 0)
            parent_new_id = self.jama_client.post_item(project=self.dst_proj_id, item_type_id=parent_type,
                                        child_item_type_id=child_type_id,
                                        location=locationItem, fields=parent_fields)
            self.id_map[parent_old_id] = parent_new_id
            return parent_new_id


        for item in sorted_items:
            item_type = item['itemType']
            fields = item['fields']
            old_id = item["id"]

            # コピーするitemの親IDを取得
            parent_info = item.get("baselineLocation", {}).get("parent", {})
            parent_ids = parent_info.get("item")

            if parent_ids: # 親IDが存在する場合
                parent_old_id = parent_ids[0]
                parent_new_id = self.id_map.get(parent_old_id)
                if parent_new_id is None:
                    parent_new_id = ensure_parent_created(parent_old_id)
                locationItem = {'item': parent_new_id}

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
            for k in ['documentKey', 'globalId', 'release', 'release1']:
                if k in dct_fields:
                    del dct_fields[k]

            child_type_id = item.get('childItemType', 0)

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
            self.id_map[old_id] = new_id            

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

    print("Start copying baseline. Ver 3.0")
    baline_mgr = BaselineMgr( baseline_id,dst_proj_id,dst_location_id)
    baline_mgr.get_items()
    baline_mgr.post_items()
    baline_mgr.set_relationships()
    print(f"\nBaseline {baseline_id} のアイテムをプロジェクト {dst_proj_id} にコピーしました。")
