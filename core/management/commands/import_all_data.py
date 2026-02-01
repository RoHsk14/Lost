from django.core.management.base import BaseCommand, CommandError
import json
import re
from pathlib import Path

class Command(BaseCommand):
    help = 'Import regions, prefectures and structures from a possibly truncated UTF-16 JSON export (partial import).'

    def add_arguments(self, parser):
        parser.add_argument('--file', '-f', type=str, default='all_data.json', help='Path to the export file (default: all_data.json)')
        parser.add_argument('--output', '-o', type=str, default=None, help='Optional path to write a cleaned UTF-8 fixture with parsed objects')
        parser.add_argument('--repair', action='store_true', help='Try to repair truncated JSON by finding the largest valid prefix and parsing it')

    def handle(self, *args, **options):
        p = Path(options['file'])
        if not p.exists():
            raise CommandError(f"File not found: {p}")

        text = p.read_text(encoding='utf-16', errors='replace')

        # If repair requested, try to rebuild a valid JSON array from the truncated content
        repaired_list = None
        if options.get('repair'):
            self.stdout.write('Attempting repair to recover more objects from truncated file...')
            # Try full parse first
            try:
                full = json.loads(text)
                if isinstance(full, list):
                    repaired_list = full
            except Exception:
                # Try to find largest prefix that forms a valid JSON array
                lb = text.find('[')
                if lb != -1:
                    s = text[lb:]
                    # Binary search for largest prefix where json.loads(prefix + ']') succeeds
                    lo = 1
                    hi = len(s)
                    best = None
                    while lo <= hi:
                        mid = (lo + hi) // 2
                        candidate = s[:mid].rstrip() + ']'
                        try:
                            parsed = json.loads(candidate)
                            if isinstance(parsed, list):
                                best = candidate
                                lo = mid + 1
                            else:
                                hi = mid - 1
                        except Exception:
                            hi = mid - 1
                    if best:
                        try:
                            repaired_list = json.loads(best)
                            self.stdout.write(self.style.SUCCESS(f"Repair succeeded: recovered {len(repaired_list)} top-level objects"))
                        except Exception:
                            repaired_list = None
        # If we got a repaired list, take its objects; otherwise fallback to targeted extraction
        objs = []
        targets = [
            '"model": "core.region"',
            '"model": "core.prefecture"',
            '"model": "core.structurelocale"'
        ]

        if repaired_list is not None:
            objs = repaired_list
        else:
            for t in targets:
                start = 0
                while True:
                    idx = text.find(t, start)
                    if idx == -1:
                        break
                    # find start of object
                    obj_start = text.rfind('{', 0, idx)
                    if obj_start == -1:
                        start = idx + 1
                        continue
                    # find matching closing brace
                    depth = 0
                    i = obj_start
                    end = None
                    while i < len(text):
                        if text[i] == '{':
                            depth += 1
                        elif text[i] == '}':
                            depth -= 1
                        i += 1
                        if depth == 0:
                            end = i
                            break
                    if end is None:
                        # truncated; stop searching for this model
                        break
                    obj_text = text[obj_start:end]
                    try:
                        obj = json.loads(obj_text)
                        objs.append(obj)
                    except Exception:
                        # try to remove trailing commas before closing braces
                        fixed = re.sub(r',\s*\}', '}', obj_text)
                        try:
                            obj = json.loads(fixed)
                            objs.append(obj)
                        except Exception:
                            self.stdout.write(self.style.WARNING(f"Skipped a malformed object starting at {obj_start}"))
                    start = end

        # Partition by model
        regions = [o for o in objs if o.get('model') == 'core.region']
        prefectures = [o for o in objs if o.get('model') == 'core.prefecture']
        structures = [o for o in objs if o.get('model') == 'core.structurelocale']

        # Insert into DB
        from core.models import Region, Prefecture, StructureLocale
        region_map = {}
        pref_map = {}

        created = {'regions':0,'prefectures':0,'structures':0}
        updated = {'regions':0,'prefectures':0,'structures':0}

        for r in regions:
            oldpk = r.get('pk')
            fields = r.get('fields',{})
            name = fields.get('nom')
            code = fields.get('code')
            if not name:
                continue
            obj, created_flag = Region.objects.get_or_create(nom=name, defaults={'code': code})
            if created_flag:
                created['regions'] += 1
            else:
                # update code if missing
                changed=False
                if code and not obj.code:
                    obj.code = code
                    obj.save()
                    changed=True
                if changed:
                    updated['regions'] += 1
            region_map[oldpk] = obj

        for p in prefectures:
            oldpk = p.get('pk')
            fields = p.get('fields',{})
            name = fields.get('nom')
            code = fields.get('code')
            region_old = fields.get('region')
            if not name:
                continue
            region_obj = region_map.get(region_old)
            if region_obj is None:
                # Try to find region in DB by searching the raw text for the region object or by name
                found_name = None
                m = re.search(r'"pk"\s*:\s*' + str(region_old) + r'.{0,200}?"nom"\s*:\s*"(?P<name>[^"]+)"', text, re.DOTALL)
                if m:
                    found_name = m.group('name')
                if found_name:
                    region_obj, created_flag_r = Region.objects.get_or_create(nom=found_name)
                    if created_flag_r:
                        created['regions'] += 1
                else:
                    # try to find a region with similar name using a basic substring match on fields if available
                    self.stdout.write(self.style.WARNING(f"Skipping prefecture '{name}' because region {region_old} not found in parsed data."))
                    continue
            obj, created_flag = Prefecture.objects.get_or_create(region=region_obj, nom=name, defaults={'code':code})
            if created_flag:
                created['prefectures'] += 1
            else:
                changed=False
                if code and not obj.code:
                    obj.code=code
                    obj.save()
                    changed=True
                if changed:
                    updated['prefectures'] += 1
            pref_map[oldpk] = obj

        for s in structures:
            oldpk = s.get('pk')
            fields = s.get('fields',{})
            name = fields.get('nom')
            type_structure = fields.get('type_structure') or 'autre'
            prefecture_old = fields.get('prefecture')
            adresse = fields.get('adresse','')
            telephone = fields.get('telephone','')
            email = fields.get('email','')
            if not name:
                continue
            pref_obj = pref_map.get(prefecture_old)
            if pref_obj is None:
                # Try to find prefecture by pk inside text (maybe not parsed earlier)
                m = re.search(r'"pk"\s*:\s*' + str(prefecture_old) + r'.{0,200}?"nom"\s*:\s*"(?P<name>[^"]+)"', text, re.DOTALL)
                found_name = m.group('name') if m else None
                if found_name:
                    # Try to find a prefecture with that name across regions
                    try:
                        pref_obj = Prefecture.objects.get(nom=found_name)
                    except Prefecture.DoesNotExist:
                        self.stdout.write(self.style.WARNING(f"Prefecture '{found_name}' referred by structure '{name}' not present; skipping structure."))
                        continue
                else:
                    self.stdout.write(self.style.WARNING(f"Skipping structure '{name}' because prefecture {prefecture_old} not found in parsed data."))
                    continue
            obj, created_flag = StructureLocale.objects.get_or_create(prefecture=pref_obj, nom=name, defaults={
                'type_structure': type_structure,
                'adresse': adresse,
                'telephone': telephone,
                'email': email,
            })
            if created_flag:
                created['structures'] += 1
            else:
                changed=False
                # update fields if blank
                if not obj.adresse and adresse:
                    obj.adresse=adresse; changed=True
                if not obj.telephone and telephone:
                    obj.telephone=telephone; changed=True
                if not obj.email and email:
                    obj.email=email; changed=True
                if not obj.type_structure and type_structure:
                    obj.type_structure=type_structure; changed=True
                if changed:
                    obj.save()
                    updated['structures'] += 1

        self.stdout.write(self.style.SUCCESS(f"Imported: regions created={created['regions']} updated={updated['regions']}; prefectures created={created['prefectures']} updated={updated['prefectures']}; structures created={created['structures']} updated={updated['structures']}"))

        # Optionally, write cleaned fixture for later use
        out = {
            'regions': len(regions),
            'prefectures': len(prefectures),
            'structures': len(structures)
        }
        self.stdout.write(self.style.NOTICE(f"Parsed (available in file): {out}"))

        out_path = options.get('output')
        if out_path:
            import io
            fp = Path(out_path)
            fp.parent.mkdir(parents=True, exist_ok=True)
            try:
                with fp.open('w',encoding='utf-8') as fh:
                    json.dump(objs, fh, ensure_ascii=False, indent=2)
                self.stdout.write(self.style.SUCCESS(f"Wrote cleaned fixture to {fp}") )
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to write {fp}: {e}"))
