class BucketRepresentation():

    def __init__(self, bucket_name):

        self._s3 = boto3.client('s3')
        self._bucket = bucket_name

    def get_root_directory_keys(self, directory='/'):
        keys = []
        paginator = self._s3.get_paginator('list_objects_v2')

        for result in paginator.paginate(Bucket='metaflow-test-data', Delimiter=directory):
            for prefix in result.get('CommonPrefixes'):
                keys.append(prefix.get('Prefix'))

        return keys

    def iterate_display(self, sub_dir, indent=0):

        for obj in sub_dir['objects']:
            print(f"{'  ' * indent} {obj}")
            
        for sub_dir_obj in sub_dir['sub_dirs']:
            print(f"{'  ' * indent} {sub_dir_obj}")
            self.iterate_display(sub_dir['sub_dirs'][sub_dir_obj], indent+1)


    def get_sub_directory_keys(self, directory=''):
        dir_tree = {}
        paginator = self._s3.get_paginator('list_objects_v2')

        for result in paginator.paginate(Bucket='metaflow-test-data', Prefix=directory):
            i = 0
            for prefix in result.get('Contents'):
                p = prefix.get('Key').split("/")

                iterate_tree = dir_tree
                data = p[1:]
                for index, key in enumerate(data):

                    if key in iterate_tree.keys():
                        iterate_tree = iterate_tree[key]

                    else:
                        iterate_tree[key] = {}
                        iterate_tree = iterate_tree[key]


        def recurse(sub_dir):

            condensed = {
                "objects": [],
                "sub_dirs": {}
            }

            for key in sub_dir.keys():
                if sub_dir[key] == {}:
                    condensed['objects'].append(key)
                else:
                    condensed['sub_dirs'][key] = recurse(sub_dir[key])
                
            return condensed

        out = recurse(dir_tree)

        return out

