import requests

base_url = "https://ckan0.cf.opendata.inter.prod-toronto.ca"
params = {"id": "traffic-volumes-at-intersections-for-all-modes"}
package = requests.get(f"{base_url}/api/3/action/package_show", params=params).json()

for resource in package["result"]["resources"]:
    print(resource["name"], resource["url"])
