class Structure(dict):
    '''Hold data related to paths in an organized way.'''

    def store(self, root_path, root_path_data):
        '''Store a dict recursively as paths.'''

        changes = []
        def recursive(path, path_data):
            if type(path_data) == type(dict()) and path_data: 
                for node in path_data:
                    node_path = os.path.join(path, node)
                    node_data = path_data[node]

                    change = self.store_one(node_path, node_data)
                    changes.append(change)

                    if type(node_data) == type(dict()):
                        recursive(node_path, node_data)
            else:
                changes.append(self.store_one(path, path_data))

        recursive(root_path, root_path_data)
        self.react(changes)
        return True

    def store_one(self, path, path_data):
        '''Store a single dict or value as a path.'''

        change = []
        if path in self: 
            if '.data' in self[path] and self[path]['.data'] and not path_data:
                change = ['delete', path, None]
                self[path]['.data'] = None

            elif '.data' in self[path] and self[path]['.data'] and path_data:
                change = ['update', path, path_data]
                self[path]['.data'] = path_data
                for anscestor in self.ancestors(path):
                    a = self.get(anscestor, {})
                    a['.data'] = {}
                    self[anscestor] = a

            else:
                change = ['create', path, path_data]
                for anscestor in self.ancestors(path):
                    a = self.get(anscestor, {})
                    a['.data'] = {}
                    self[anscestor] = a
                self[path]['.data'] = path_data

        else:
            change = ['create', path, path_data]
            for anscestor in self.ancestors(path):
                a = self.get(anscestor, {})
                a['.data'] = {}
                self[anscestor] = a
            self[path] = {'.data': path_data}

        return change

    def react(self, log):
        '''Call events based on a list of changes.'''

        for action,path,value in sorted(log, key=lambda d: len(d[1])):
            # If the path contains a . (i.e. it's meta data), just ignore it and don't call anything
            if not '.' in path: 
                all_ancestors = self.ancestors(path)
                parent = all_ancestors[0]
                ancestors = all_ancestors[1:]

                if action == 'create':
                    self.trigger(path, 'value', data=value) 
                    if value:
                        self.trigger(parent, 'child_added', data=value, snapshotPath=path)

                    for a in all_ancestors:
                        self.trigger(a, 'value', data=self.objectify(a))

                if action == 'update':
                    self.trigger(path, 'value', data=value)
                    for a in all_ancestors:
                        self.trigger(a, 'child_changed', data=value, snapshotPath=path)
                        self.trigger(a, 'value', data=self.objectify(a))

                if action == 'delete':
                    data = self.objectify(path)
                    self.trigger(path, 'value', data=data)
                    self.trigger(parent, 'child_removed', data=data, snapshotPath=path)

                    for a in all_ancestors:
                        self.trigger(a, 'value', data=self.objectify(a))

    def trigger(self, path, event, data, snapshotPath=None):
        '''Call all functions related to an event on path.'''

        event_key = '.event-'+event

        if not snapshotPath:
            snapshotPath = path

        if path in self:
            path_node = self[path]
            if path_node and event_key in path_node:
                # If the "updated" data and the old data are the same, don't do anything
                if data != path_node.get('.last-data'):
                    if data==None:
                        # If data is None, we pass the old data (for DELETE)
                        snapshotData = path_node.get('.last-data')
                    else:
                        # Otherwise we just set last-data appropriately and set snapshotData to the new data
                        path_node['.last-data'] = data
                        snapshotData = data

                    callbacks = path_node[event_key]

                    obj = DataSnapshot(snapshotPath, snapshotData)

                    for callback in callbacks:
                        callback(obj)
            else:
                return False
        else:
            return False


    def objectify(self, path):
        '''Return an object version of a path.'''

        def recursive(rpath):
            obj = {}
            data = self[rpath].get('.data', {})

            children_paths = self.children(rpath)
            children_last_nodes = self.last_nodes(children_paths)

            if type(data) != type(dict()):
                return data

            for key in children_last_nodes:
                kpath = os.path.join(rpath, key)
                kpath_node = self[kpath]
                if '.data' in kpath_node:
                    kpath_data = kpath_node['.data']
                    if kpath_data or kpath_data == {}:
                        if type(kpath_data) == type(dict()):
                            obj[key] = recursive(kpath)
                            if obj[key] == {}:
                                obj.pop(key)
                        else:
                            obj[key] = kpath_data

            return obj

        obj = recursive(path)
        return obj

    def children(self, parent):
        '''Return direct children of path in self.'''

        parent_nodes = self.nodes(parent)
        children = []
        for path in self:
            path_nodes = self.nodes(path)
            if path_nodes[:len(parent_nodes)] == parent_nodes and len(path_nodes) == len(parent_nodes) + 1:
                children.append(path)
        return children


    def descendants(self, parent):
        '''Return all descendants of path in self.'''

        parent_nodes = self.nodes(parent)
        children = []
        for path in self:
            path_nodes = self.nodes(path)
            if path_nodes[:len(parent_nodes)] == parent_nodes and path_nodes != parent_nodes:
                children.append(path)
        return children

    def ancestors(self, path):
        '''Return all anscestors of a path.'''

        nodes = path.split('/')
        ancestors = []
        for n in range(0, len(nodes)):
            ancestors.append('/'.join(nodes[:-n]))
        return [a for a in ancestors if a]

    def nodes(self, path):
        '''Returns a list containing individual nodes in a path.'''

        dirty_nodes = path.split('/')
        clean_nodes = []
        for node in dirty_nodes:
            if node:
                clean_nodes.append(node)
        return clean_nodes

    def first_node(self, path):
        '''Return the first node in a path.'''

        nodes = self.nodes(path)
        return nodes[0]

    def last_node(self, path):
        '''Return the last node in a path.'''

        nodes = self.nodes(path)
        return nodes[-1:][0]

    def first_nodes(self, paths):
        '''Return the first nodes for each path in paths.'''

        nodes = []
        for path in paths:
            first_node = self.first_node(path)
            nodes.append(first_node)
        return nodes


    def last_nodes(self, paths):
        '''Return the last nodes for each path in paths.'''

        nodes = []
        for path in paths:
            last_node = self.last_node(path)
            nodes.append(last_node)
        return nodes