from pathlib import Path

import yaml
from django.conf import settings
from django.test import SimpleTestCase
from drf_spectacular.generators import SchemaGenerator
from drf_spectacular.renderers import OpenApiYamlRenderer


class OpenAPIContractSnapshotTests(SimpleTestCase):
    def test_checked_in_contract_matches_generated_schema(self):
        generated = SchemaGenerator().get_schema(request=None, public=True)
        normalized = yaml.safe_load(OpenApiYamlRenderer().render(generated))
        frozen = yaml.safe_load((Path(settings.BASE_DIR) / "docs/openapi-v1.yaml").read_text())
        self.assertEqual(normalized, frozen, "Regenerate docs/openapi-v1.yaml with manage.py spectacular")
