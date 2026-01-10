from amelia.features.barnstormers import services
from .barnstormers_sample import sample, thumb_sample

def test_barn():
    classifieds = services.get_classifieds(sample)
    assert False
