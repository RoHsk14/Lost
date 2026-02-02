from django.test import TestCase, Client
from django.urls import reverse
from .models import Region, Prefecture, StructureLocale


class ApiRegionPrefectureStructureTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create regions
        self.r1 = Region.objects.create(nom='Region A', code='RGA')
        self.r2 = Region.objects.create(nom='Region B', code='RGB')

        # Prefectures
        self.p1 = Prefecture.objects.create(nom='Pref A1', region=self.r1, code='PA1')
        self.p2 = Prefecture.objects.create(nom='Pref A2', region=self.r1, code='PA2')
        self.p3 = Prefecture.objects.create(nom='Pref B1', region=self.r2, code='PB1')

        # Structures locales
        self.s1 = StructureLocale.objects.create(nom='Structure 1', type_structure='mairie', prefecture=self.p1)
        self.s2 = StructureLocale.objects.create(nom='Structure 2', type_structure='commissariat', prefecture=self.p1)
        self.s3 = StructureLocale.objects.create(nom='Structure 3', type_structure='gendarmerie', prefecture=self.p3)

    def test_api_regions_returns_regions(self):
        resp = self.client.get('/api/regions/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        # Expect at least two regions
        noms = {r['nom'] for r in data}
        self.assertIn('Region A', noms)
        self.assertIn('Region B', noms)

    def test_api_prefectures_for_region(self):
        # Test API view (api_views) endpoint: /api/prefectures/region/<id>/
        resp = self.client.get(f'/api/prefectures/region/{self.r1.id}/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        noms = {p.get('nom') for p in data}
        self.assertIn('Pref A1', noms)
        self.assertIn('Pref A2', noms)
        self.assertNotIn('Pref B1', noms)

        # Test query endpoint: /api/query/prefectures/?region=<id>
        resp2 = self.client.get(f'/api/query/prefectures/?region={self.r1.id}')
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.json()
        noms2 = {p.get('nom') for p in data2}
        self.assertIn('Pref A1', noms2)
        self.assertIn('Pref A2', noms2)

    def test_api_structures_for_prefecture(self):
        # Test API view (api_views) endpoint: /api/structures/prefecture/<id>/
        resp = self.client.get(f'/api/structures/prefecture/{self.p1.id}/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        noms = {s['nom'] for s in data}
        self.assertIn('Structure 1', noms)
        self.assertIn('Structure 2', noms)
        self.assertNotIn('Structure 3', noms)

        # Test query endpoint: /api/query/structures/?prefecture=<id>
        resp2 = self.client.get(f'/api/query/structures/?prefecture={self.p1.id}')
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.json()
        noms2 = {s.get('nom') for s in data2}
        self.assertTrue(any('Structure 1' in n for n in noms2))
        self.assertTrue(any('Structure 2' in n for n in noms2))

    def test_router_prefectures_list_viewset(self):
        # Router endpoint (DRF viewset) listing all prefectures
        resp = self.client.get('/api/prefectures/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        # DRF may paginate results -> handle dict with 'results' or raw list
        items = data.get('results') if isinstance(data, dict) and 'results' in data else data
        found = False
        for item in items:
            if item.get('nom') == 'Pref A1' and isinstance(item.get('region'), dict):
                found = True
        self.assertTrue(found)

    def test_router_structures_list_viewset(self):
        resp = self.client.get('/api/structures_locales/')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        noms = {s['nom'] for s in data}
        self.assertIn('Structure 1', noms)
        self.assertIn('Structure 3', noms)
