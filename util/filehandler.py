import os
import os.path
import csv

class filehandlerbase:
    def __init__(self, filename, mode='w', delimiter=''):
        #filename = filename.strip("/\*?:\"\'<>|")
        self.pathcreate(filename)
        self.mode = mode
        self.splitfilename = filename.rsplit('.', 1)
        self.newfile = not self.fileexist(filename)
        if not self.fileexist(filename) or self.mode == 'a':
            self.filename = filename
        else:
            self.i = 1
            searchfile = True
            while searchfile > 0:
                if self.i < 10:
                    self.filename = self.splitfilename[0] + '_0%i.' %self.i + self.splitfilename[1]
                    searchfile = self.fileexist(self.filename)
                else:
                    self.filename = self.splitfilename[0] + '_%i.' %self.i + self.splitfilename[1]
                    searchfile = self.fileexist(self.filename)
                self.i+=1
                if self.i == 99:
                    searchfile = False
                    self.mode='a'

        self.f = open(self.filename, mode)
        if delimiter == '':
            if self.splitfilename[1].lower() == 'prn':
                self.delimiter = '\t'
            else:
                self.delimiter = ','
        else:
            self.delimiter = delimiter

    def flush(self):
        self.f.flush()

    def close(self):
        self.f.close()

    def pathcreate(self, filename):
        pathname = os.path.split(filename)[0]
        if not os.path.isdir(pathname) and not pathname == '':
            dirsplit = pathname.split('\\')
            if len(dirsplit) == 1:
                dirsplit = pathname.split('/')

            dircreate = ''
            for n, name in enumerate(dirsplit):
                dircreate += name + '\\'
                if n:
                    if not os.path.isdir(dircreate):
                        try:
                            os.mkdir(dircreate)
                        except WindowsError, error:
                            if error[0:30].find('17') > 0:
                                pass

    def fileexist(self, filename):
        return os.path.isfile(filename)

    def writerow(self, data):
        self.CSV.writerow(data)

    def write(self, data):
        self.f.write(data)

class filehandler(filehandlerbase):
    def __init__(self, filename, headings=[], delimiter=''):
        filehandlerbase.__init__(self, filename, delimiter=delimiter)

        self.CSV = csv.writer(self.f, dialect='excel', delimiter=self.delimiter, lineterminator='\n')

        self.CSV.writerow(headings)
        self.f.flush()

class dictwriter(filehandlerbase):
    def __init__(self, filename, headings, mode='a'):
        filehandlerbase.__init__(self, filename, mode)

        self.CSV = csv.DictWriter(self.f, headings, delimiter=self.delimiter, lineterminator='\n')

        if self.newfile:
            self.CSV.writerow(dict(zip(headings, headings)))
            self.f.flush()

class logfile(filehandlerbase):
    def __init__(self, filename, headings = [], mode='a'):
        self.mode = mode
        filehandlerbase.__init__(self, filename, self.mode)

        self.CSV = csv.writer(self.f, delimiter=self.delimiter, lineterminator='\n')

        if self.newfile and headings:
            self.CSV.writerow(headings)
            self.f.flush()