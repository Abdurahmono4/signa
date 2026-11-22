"""Read the pinned MaDiS release's three synchronized How2Sign codebook streams."""
import hashlib
import io
import re
from contextlib import contextmanager
from zipfile import ZipFile

ARCHIVE_NAME = 'TOKENS_h2s_csl_phoenix.zip'
ARCHIVE_SHA256 = 'b544ad2d2ba13f51bff8b7226fe22511f0ff636965148c7b1a5751a7a200743d'
PREFIX = 'TOKENS_h2s_csl_phoenix/how2sign/'


@contextmanager
def open_verified(path):
    with path.open('rb') as handle:
        if hashlib.file_digest(handle, 'sha256').hexdigest() != ARCHIVE_SHA256:
            raise ValueError('Unexpected MaDiS token archive checksum')
        handle.seek(0)
        with ZipFile(handle) as archive:
            yield archive


def read_tokens(archive, sentence):
    import numpy as np
    if not re.fullmatch(r'[a-zA-Z0-9_-]+-rgb_front', sentence):
        raise ValueError('Invalid How2Sign frontal sentence ID')
    info = archive.getinfo(PREFIX + sentence + '.npy')
    if info.file_size > 64 * 1024:
        raise ValueError('Oversized reference sequence')
    codes = np.load(io.BytesIO(archive.read(info)), allow_pickle=False)
    if codes.ndim != 3 or codes.shape[0]!=1 or codes.shape[2]!=3 or codes.dtype.kind not in 'iu':
        raise ValueError('Expected one integer T-by-3 sequence')
    if not 1 <= codes.shape[1] <= 100:
        raise ValueError('Reference duration outside supported 4–400 frames')
    codes = codes[0]
    if np.any(codes < 0) or np.any(codes >= np.array([96,192,192])):
        raise ValueError('Reference code outside the released codebook')
    return codes
