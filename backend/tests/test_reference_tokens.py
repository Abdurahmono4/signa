import io
from zipfile import ZipFile

import numpy as np
import pytest

from backend.app.inference.reference_tokens import PREFIX, open_verified, read_tokens


def archive_with(array, prefix=PREFIX):
    file = io.BytesIO()
    np.save(file, array, allow_pickle=False)
    data = io.BytesIO()
    with ZipFile(data, 'w') as archive:
        archive.writestr(prefix + 'fixture-rgb_front.npy', file.getvalue())
    return ZipFile(data)


def test_release_ids_are_dataset_specific_and_three_codebooks_are_ordered(tmp_path):
    expected = np.array([[[95, 191, 130], [0, 140, 190]]], dtype=np.uint16)
    with archive_with(expected) as archive:
        np.testing.assert_array_equal(read_tokens(archive, 'fixture-rgb_front'), expected[0])
        with pytest.raises(ValueError):read_tokens(archive, '../fixture-rgb_front')
    with archive_with(expected, 'TOKENS_h2s_csl_phoenix/csl/') as archive:
        with pytest.raises(KeyError):read_tokens(archive, 'fixture-rgb_front')
    wrong = tmp_path / 'changed.zip'
    wrong.write_bytes(b'not the pinned research archive')
    with pytest.raises(ValueError, match='checksum'), open_verified(wrong):
        pass


@pytest.mark.parametrize('array', [
    np.zeros((1, 0, 3), dtype='int32'), np.zeros((1, 101, 3), dtype='int32'),
    np.zeros((1, 5, 2), dtype='int32'), np.zeros((1, 2, 3), dtype='float32'),
    np.array([[[96, 3, 4]]]), np.array([[[1, 192, 3]]]), np.array([[[1, 3, -1]]]),
])
def test_invalid_reference_codes_are_rejected(array):
    with archive_with(array) as archive, pytest.raises(ValueError):
        read_tokens(archive, 'fixture-rgb_front')
