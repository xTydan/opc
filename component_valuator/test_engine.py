import unittest
from engine import infer_specs, compatibility, robust_price, value_component, parse_import

class ValuationTests(unittest.TestCase):
    def test_ram_class_requires_same_generation_and_capacity(self):
        target={"category":"ram","model":"DDR5 16GB 5600MHz","specs":infer_specs("ram","DDR5 16GB 5600MHz")}
        same={"category":"ram","model":"Corsair DDR5 16GB 5600MHz","specs":infer_specs("ram","Corsair DDR5 16GB 5600MHz")}
        ddr4={"category":"ram","model":"DDR4 16GB 3200MHz","specs":infer_specs("ram","DDR4 16GB 3200MHz")}
        self.assertGreater(compatibility(target,same)[0],0)
        self.assertEqual(compatibility(target,ddr4)[0],0)

    def test_storage_rejects_different_interface(self):
        a={"category":"storage","model":"NVMe SSD 1TB","specs":infer_specs("storage","NVMe SSD 1TB")}
        b={"category":"storage","model":"SATA SSD 1TB","specs":infer_specs("storage","SATA SSD 1TB")}
        self.assertEqual(compatibility(a,b)[0],0)

    def test_outlier_resistant_median(self):
        price,used=robust_price([400,420,430,440,3000])
        self.assertEqual(price,430)
        self.assertNotIn(3000,used)

    def test_no_price_below_five_matches(self):
        target={"category":"ram","model":"DDR5 16GB","specs":infer_specs("ram","DDR5 16GB")}
        offers=[{"category":"ram","model":f"Brand {i} DDR5 16GB","price":100+i,"specs":infer_specs("ram",f"Brand {i} DDR5 16GB")} for i in range(4)]
        result=value_component(target,offers)
        self.assertIsNone(result["estimated_market_price"])
        self.assertEqual(result["confidence"],"brak danych")

    def test_import_raw_scraper_listings(self):
        rows=parse_import({"listings":[{"title":"PC Ryzen 5 5600 RTX 3060","description":"RAM DDR5 16GB 5600MHz SSD NVMe 1TB","price":2200}]})
        self.assertEqual(len(rows),1)
        self.assertGreaterEqual(len(rows[0]["components"]),3)

if __name__=="__main__": unittest.main()
