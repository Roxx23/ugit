from . import data
import os

def write_tree(directory='.'):
    entries = []
    with os.scandir(directory) as it:
        for entry in it:
            full = os.path.join(directory, entry.name)
            if is_ignored(full):
                continue
            if entry.is_file(follow_symlinks=False):
                type_ = 'blob'
                with open(full, 'rb') as f:
                    oid = data.hash_object(f.read())
            elif entry.is_dir(follow_symlinks=False):
                type_ = 'tree'
                oid = write_tree(full)
            entries.append((entry.name, oid, type_))
    tree = ''.join (f'{type_} {oid} {name}\n' for name, oid, type_ in sorted(entries))
    return data.hash_object(tree.encode(), type_ = 'tree')

def is_ignored(path):
    return '.ugit' in path.split(os.sep) or 'env' in path.split(os.sep) or '.git' in path.split(os.sep)

def _iter_tree_entries(oid):
    if not oid:
        return
    tree = data.get_object(oid, 'tree')
    for entry in tree.decode().splitlines():
        type_, oid, name = entry.split(' ', 2)
        yield type_, oid, name

def get_tree(oid, base_path = ''):
    result = {}
    for type_, oid, name in _iter_tree_entries(oid):
        path = os.path.join(base_path, name)
        if type_ == 'blob':
            result[path] = oid
        elif type_ == 'tree':
            result.update(get_tree(oid, path))
        else:
            assert False, f'Unknown tree entry type: {type_}'
    return result

def _empty_current_directory():
    for root, dirnames, filenames in os.walk('.', topdown=False):
        for filename in filenames:
            if is_ignored(os.path.join(root, filename)):
                continue
            os.remove(os.path.join(root, filename))
        for dirname in dirnames:
            if is_ignored(os.path.join(root, dirname)):
                continue
            try:
                os.rmdir(os.path.join(root, dirname))
            except OSError:
                pass

def read_tree(tree_oid):
    _empty_current_directory()
    for path, oid in get_tree(tree_oid, base_path='./').items():
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(data.get_object(oid, 'blob'))

def commit(message):
    commit = f'tree {write_tree()}\n'
    commit_data = f'tree {write_tree()}\n'
    HEAD = data.get_HEAD()
    if HEAD:
        commit += f'parent {HEAD}\n'
    commit += '\n'
    commit += f'{message}\n'
    oid = data.hash_object(commit.encode(), type_ = 'commit')
        commit_data += f'parent {HEAD}\n'
    commit_data += '\n'
    commit_data += f'{message}\n'
    oid = data.hash_object(commit_data.encode(), type_ = 'commit')
    data.set_head(oid)
    return oid