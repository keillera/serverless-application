import glob
import re
from distutils.dir_util import copy_tree

for name in glob.iglob('tests/**/test*.py', recursive=True):
    test_dir = re.sub('/test_.*\.py$', '', name)
    copy_tree(re.sub('^tests', 'src', test_dir), test_dir)
    copy_tree('common', test_dir)
