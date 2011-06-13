"""
The annotationmodel module contains the classes for the AnnotationModel.
"""
from PyQt4.QtGui import QTreeView, QSortFilterProxyModel, QAbstractItemView
from PyQt4.QtCore import QObject, QModelIndex, QPersistentModelIndex, QAbstractItemModel, QVariant, Qt, pyqtSignal
import os.path

ItemRole, TypeRole, DataRole, ImageRole = [Qt.UserRole + i + 1 for i in range(4)]

class ModelItem(QObject):
    def __init__(self):
        self.children_ = []
        self._pindex   = None
        self.model_    = None
        self.parent_   = None

    def children(self):
        return self.children_

    def model(self):
        return self.model_

    def parent(self):
        assert self.parent_ != self
        return self.parent_

    def data(self, role=Qt.DisplayRole, column=0):
        if role == ItemRole:
            return QVariant(self)
        else:
            return QVariant()

    def setParent(self, parent):
        assert self.parent_ is None
        self.parent_ = parent

    def setIndex(self, index):
        assert self._pindex is None
        self._pindex = QPersistentModelIndex(index)
        if index.isValid():
            self.model_ = index.model()

    def pindex(self):
        assert self._pindex is not None
        return self._pindex

    def index(self, column=0):
        # TODO: The two columns can probably be handled better...
        # Maybe use a list of indices, with the second being QModelIndex()
        # for everything except the KeyValueModelItems?
        assert self._pindex is not None
        if column != 0:
            return QModelIndex()
        return QModelIndex(self._pindex)

    def parentIndex(self):
        if self.parent_ is not None:
            return self.parent_.index()
        else:
            return QModelIndex()

    def appendChild(self, item):
        next_row = len(self.children_)
        index = self.index()
        self.model_.beginInsertRows(index, next_row, next_row)
        self.children_.append(item)
        item.setParent(self)
        self.model_.endInsertRows()
        item_index = self.model().createIndex(next_row, 0, item)
        item.setIndex(item_index)

    def deleteAllChildren(self):
        for child in self.children_:
            child.deleteAllChildren()

        self.model_.beginRemoveRows(self.index(), 0, len(self.children_) - 1)
        self.children_ = []
        self.model_.endRemoveRows()

    def delete(self):
        if self.parent() is None:
            raise RuntimeError("Trying to delete orphan")
        else:
            self.parent().deleteChild(self)

    def deleteChild(self, arg):
        if isinstance(arg, ModelItem):
            self.deleteChild(self.children_.index(arg))
        else:
            if arg < 0 or arg >= len(self.children_):
                raise IndexError("child index out of range")
            self.children_[arg].deleteAllChildren()
            self.model_.beginRemoveRows(self.index(), arg, arg)
            del self.children_[arg]
            self.model_.endRemoveRows()

class RootModelItem(ModelItem):
    def __init__(self, model):
        ModelItem.__init__(self)
        self.model_ = model
        self.setIndex(QModelIndex())

    def appendChild(self, item):
        if isinstance(item, FileModelItem):
            ModelItem.appendChild(self, item)
        else:
            raise TypeError("Only FileModelItems can be attached to RootModelItem")

    def appendFileItem(self, fileinfo):
        item = FileModelItem.create(fileinfo)
        self.appendChild(item)

    def appendFileItems(self, fileinfos):
        for fileinfo in fileinfos:
            self.appendFileItem(fileinfo)

class FileModelItem(ModelItem):
    def __init__(self, fileinfo):
        ModelItem.__init__(self)
        self._fileinfo = fileinfo

    def filename(self):
        return self._fileinfo['filename']

    def data(self, role=Qt.DisplayRole, column=0):
        if role == Qt.DisplayRole and column == 0:
            return os.path.basename(self.filename())
        return ModelItem.data(self, role, column)

    @staticmethod
    def create(fileinfo):
        if fileinfo['type'] == 'image':
            return ImageFileModelItem(fileinfo)
        elif fileinfo['type'] == 'video':
            return VideoFileModelItem(fileinfo)

class ImageModelItem(ModelItem):
    pass

class ImageFileModelItem(FileModelItem, ImageModelItem):
    def __init__(self, fileinfo):
        FileModelItem.__init__(self, fileinfo)

        for ann in fileinfo['annotations']:
            item = AnnotationModelItem(ann)
            self.appendChild(item)

    def addAnnotation(self, ann):
        self.fileinfo_['annotations'].append(ann)
        item = AnnotationModelItem(ann)
        self.appendChild(item)

    # TODO
    def updateAnnotation(self, ann):
        child_found = False
        for child in self.children_:
            if child.type() == ann['type']:
                if (child.has_key('id') and ann.has_key('id') and child.value('id') == ann['id']) or (not child.has_key('id') and not ann.has_key('id')):
                    ann[None] = None
                    #child.setData(index, QVariant(ann), DataRole)
                    child_found = True
                    break
        if not child_found:
            raise Exception("No ImageFileModelItem found that could be updated!")

    def removeAnnotation(self, pos):
        del self.fileinfo_['annotations'][pos]
        self.deleteChild(pos)

    def data(self, role=Qt.DisplayRole, column=0):
        if role == DataRole:
            return self.fileinfo_
        return FileModelItem.data(self, role)

class VideoFileModelItem(FileModelItem):
    def __init__(self, fileinfo):
        FileModelItem.__init__(self, fileinfo)

        for frameinfo in fileinfo['frames']:
            item = FrameModelItem(frameinfo)
            self.appendChild(item)

class FrameModelItem(ImageModelItem):
    def __init__(self, frameinfo):
        ModelItem.__init__(self)
        self.frameinfo_ = frameinfo

        for ann in frameinfo['annotations']:
            item = AnnotationModelItem(ann)
            self.appendChild(item)

    def framenum(self):
        return int(self.frameinfo_.get('num', -1))

    def timestamp(self):
        return float(self.frameinfo_.get('timestamp', -1))

    def addAnnotation(self, ann):
        self.frameinfo_['annotations'].append(ann)
        item = AnnotationModelItem(ann)
        self.appendChild(item)

    # TODO
    def updateAnnotation(self, ann):
        child_found = False
        for child in self.children_:
            if child.type() == ann['type']:
                if (child.has_key('id') and ann.has_key('id') and child.value('id') == ann['id']) or (not child.has_key('id') and not ann.has_key('id')):
                    ann[None] = None
                    #child.setData(index, QVariant(ann), DataRole)
                    child_found = True
                    break
        if not child_found:
            raise Exception("No FrameModelItem found that could be updated!")

    def removeAnnotation(self, pos):
        del self.frameinfo_['annotations'][pos]
        self.deleteChild(pos)

    def data(self, index, role=Qt.DisplayRole, column=0):
        if role == Qt.DisplayRole and index.column() == 0:
            return "%d / %.3f" % (self.framenum(), self.timestamp())
        return QVariant()

class AnnotationModelItem(ModelItem):
    def __init__(self, annotation):
        ModelItem.__init__(self)
        self.annotation_ = annotation
        # dummy key/value so that pyqt does not convert the dict
        # into a QVariantMap while communicating with the Views
        self.annotation_[None] = None

        for key, value in annotation.iteritems():
            if key == None:
                continue
            self.addChild(KeyValueModelItem(key))

    def type(self):
        return self.annotation_['type']

    def setData(self, index, data, role):
        if role == DataRole:
            print self.annotation_
            data = data.toPyObject()
            print data, type(data)
            print self.annotation_
            for key, value in data.iteritems():
                print key, value
                if not key in self.annotation_:
                    print "not in annotation: ", key
                    self.addChild(KeyValueModelItem(key))
                    self.annotation_[key] = data[key]

            for key in self.annotation_.keys():
                if not key in data:
                    # TODO
                    self.deleteChild() # TODO
                    del self.annotation_[key]
                else:
                    self.annotation_[key] = data[key]
                    # TODO: Emit data changed signal

            print "new annotation:", self.annotation_
            # TODO: Emit data changed signal
            return True
        return False

    def data(self, index, role=Qt.DisplayRole, column=0):
        if role == Qt.DisplayRole and column == 0:
            return self.type()
        elif role == TypeRole:
            return self.type()
        elif role == DataRole:
            return self.annotation_
        return QVariant()

    def setValue(self, key, value):
        self.annotation_[key] = value
        # TODO: Emit data changed signal

    def value(self, key):
        return self.annotation_[key]

    def has_key(self, key):
        return self.annotation_.has_key(key)

class KeyValueModelItem(ModelItem):
    def __init__(self, key):
        ModelItem.__init__(self)
        self._key = key

    def data(self, role=Qt.DisplayRole, column=0):
        if role == Qt.DisplayRole:
            if column == 0:
                return self._key
            elif column == 1:
                return self.parent().value(self._key)
            else:
                return QVariant()

class AnnotationModel(QAbstractItemModel):
    # signals
    dirtyChanged = pyqtSignal(bool, name='dirtyChanged')

    def __init__(self, annotations, parent=None):
        QAbstractItemModel.__init__(self, parent)
        self.annotations_ = annotations
        self.dirty_       = False
        self.root_        = RootModelItem(self)
        self.root_.appendFileItems(self.annotations_)

    # QAbstractItemModel overloads
    def columnCount(self, index=QModelIndex()):
        return 2

    def rowCount(self, index=QModelIndex()):
        item = self.itemFromIndex(index)
        return len(item.children())

    def parent(self, index):
        if index is None:
            return QModelIndex()
        item = self.itemFromIndex(index)
        parent = item.parent()
        if parent is None:
            return QModelIndex()
        return parent.index()

    def index(self, row, column, parent_idx=QModelIndex()):
        parent = self.itemFromIndex(parent_idx)
        if row >= len(parent.children()):
            return QModelIndex()
        return parent.children()[row].index(column)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return QVariant()
        item = self.itemFromIndex(index)
        return item.data(role, index.column())

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid():
            return False
        item = self.itemFromIndex(index)
        return item.setData(index, value, role)

    def flags(self, index):
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section == 0:   return QVariant("File/Type/Key")
            elif section == 1: return QVariant("Value")
        return QVariant()

    # Own methods
    def dirty(self):
        return self.dirty_

    def setDirty(self, dirty=True):
        if dirty != self.dirty_:
            self.dirty_ = dirty
            self.dirtyChanged.emit(self.dirty_)

    def itemFromIndex(self, index):
        index = QModelIndex(index)  # explicitly convert from QPersistentModelIndex
        if index.isValid():
            return index.internalPointer()
        return self.root_


#######################################################################################
# proxy model
#######################################################################################

class AnnotationSortFilterProxyModel(QSortFilterProxyModel):
    """Adds sorting and filtering support to the AnnotationModel without basically
    any implementation effort.  Special functions such as ``insertPoint()`` just
    call the source models respective functions."""
    def __init__(self, parent=None):
        super(AnnotationSortFilterProxyModel, self).__init__(parent)

    def fileIndex(self, index):
        fi = self.sourceModel().fileIndex(self.mapToSource(index))
        return self.mapFromSource(fi)

    def itemFromIndex(self, index):
        return self.sourceModel().itemFromIndex(self.mapToSource(index))

    def baseDir(self):
        return self.sourceModel().baseDir()

    def insertPoint(self, pos, parent, **kwargs):
        return self.sourceModel().insertPoint(pos, self.mapToSource(parent), **kwargs)

    def insertRect(self, rect, parent, **kwargs):
        return self.sourceModel().insertRect(rect, self.mapToSource(parent), **kwargs)

    def insertMask(self, fname, parent, **kwargs):
        return self.sourceModel().insertMask(fname, self.mapToSource(parent), **kwargs)

    def insertFile(self, filename):
        return self.sourceModel().insertFile(filename)


#######################################################################################
# view
#######################################################################################

class AnnotationTreeView(QTreeView):
    def __init__(self, parent=None):
        super(AnnotationTreeView, self).__init__(parent)

        self.setUniformRowHeights(True)
        self.setSelectionMode(QTreeView.SingleSelection)
        self.setSelectionBehavior(QTreeView.SelectItems)
        self.setAllColumnsShowFocus(True)
        self.setAlternatingRowColors(True)
        self.setEditTriggers(QAbstractItemView.SelectedClicked)
        self.setSortingEnabled(True)
        self.expanded.connect(self.onExpanded)

    def resizeColumns(self):
        for column in range(self.model().columnCount(QModelIndex())):
            self.resizeColumnToContents(column)

    def onExpanded(self):
        self.resizeColumns()

    def setModel(self, model):
        QTreeView.setModel(self, model)
        self.resizeColumns()

    def keyPressEvent(self, event):
        ## handle deletions of items
        if event.key() == Qt.Key_Delete:
            self.model().itemFromIndex(self.currentindex()).delete()

        ## it is important to use the keyPressEvent of QAbstractItemView, not QTreeView
        QAbstractItemView.keyPressEvent(self, event)

    def rowsInserted(self, index, start, end):
        QTreeView.rowsInserted(self, index, start, end)
        self.resizeColumns()
#        self.setCurrentIndex(index.child(end, 0))
