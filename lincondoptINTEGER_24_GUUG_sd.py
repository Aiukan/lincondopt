from ctypes import BigEndianStructure
import random
import tkinter
import copy
from tkinter import ttk
from tkinter import filedialog
import numpy
import math
from collections import deque

class DoubleScrolledFrame:
    def __init__(self, master, **kwargs):
        width = kwargs.pop('width', None)
        height = kwargs.pop('height', None)
        self.outer = tkinter.Frame(master, **kwargs)

        self.vsb = ttk.Scrollbar(self.outer, orient=tkinter.VERTICAL)
        self.vsb.grid(row=0, column=1, sticky='ns')
        self.hsb = ttk.Scrollbar(self.outer, orient=tkinter.HORIZONTAL)
        self.hsb.grid(row=1, column=0, sticky='ew')
        self.canvas = tkinter.Canvas(self.outer, highlightthickness=0, width=width, height=height)
        self.canvas.grid(row=0, column=0, sticky='nsew')
        self.outer.rowconfigure(0, weight=1)
        self.outer.columnconfigure(0, weight=1)
        self.canvas['yscrollcommand'] = self.vsb.set
        self.canvas['xscrollcommand'] = self.hsb.set
        # mouse scroll does not seem to work with just "bind"; You have
        # to use "bind_all". Therefore to use multiple windows you have
        # to bind_all in the current widget
        self.canvas.bind("<Enter>", self._bind_mouse)
        self.canvas.bind("<Leave>", self._unbind_mouse)
        self.vsb['command'] = self.canvas.yview
        self.hsb['command'] = self.canvas.xview

        self.inner = tkinter.Frame(self.canvas)
        # pack the inner Frame into the Canvas with the topleft corner 4 pixels offset
        self.canvas.create_window(4, 4, window=self.inner, anchor='nw')
        self.inner.bind("<Configure>", self._on_frame_configure)

        self.outer_attr = set(dir(tkinter.Widget))

    def __getattr__(self, item):
        if item in self.outer_attr:
            # geometry attributes etc (eg pack, destroy, tkraise) are passed on to self.outer
            return getattr(self.outer, item)
        else:
            # all other attributes (_w, children, etc) are passed to self.inner
            return getattr(self.inner, item)

    def _on_frame_configure(self, event=None):
        x1, y1, x2, y2 = self.canvas.bbox("all")
        height = self.canvas.winfo_height()
        width = self.canvas.winfo_width()
        self.canvas.config(scrollregion = (0,0, max(x2, width), max(y2, height)))

    def _bind_mouse(self, event=None):
        self.canvas.bind_all("<4>", self._on_mousewheel)
        self.canvas.bind_all("<5>", self._on_mousewheel)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_mouse(self, event=None):
        self.canvas.unbind_all("<4>")
        self.canvas.unbind_all("<5>")
        self.canvas.unbind_all("<MouseWheel>")
        
    def _on_mousewheel(self, event):
        """Linux uses event.num; Windows / Mac uses event.delta"""
        func = self.canvas.xview_scroll if event.state & 1 else self.canvas.yview_scroll 
        if event.num == 4 or event.delta > 0:
            func(-1, "units" )
        elif event.num == 5 or event.delta < 0:
            func(1, "units" )
    
    def __str__(self):
        return str(self.outer)

# копирует входящие данные
class StartBatch:
    def __init__(self, parent):
        self.A = copy.deepcopy(parent.A)    
        self.b = copy.deepcopy(parent.b)
        self.c = copy.deepcopy(parent.c)
        self.c0 = copy.deepcopy(parent.c)
        self.constrSigns = copy.deepcopy(parent.constrSigns)
        self.xSigns = copy.deepcopy(parent.xSigns)
        self.xInteger = copy.deepcopy(parent.xInteger)
        self.optimization = copy.deepcopy(parent.optimization)

# окно ввода значений в таблицу
class LinearOptimizationSolver(tkinter.Tk):
    def __init__(self):
        super().__init__()
        self.title("Линейная условная оптимизация")
        self.grid_rowconfigure(0, weight = 1)
        self.grid_columnconfigure(0, weight = 1)

        s = ttk.Style()
        s.configure('my.TButton', font=('Helvetica', 12))
        s.configure('my.TRadiobutton', font=('Helvetica', 12))

        self.startFrame = StartFrame(self)
        self.startFrame.grid(row = 0, column = 0)
        self.constructed = False

        self.gridFrame = GridFrame(self)

        self.settingsFrame = SettingsFrame(self)

        self.tk.call("tk", "windowingsystem")
        self.option_add("*tearOff", tkinter.FALSE)
        
        self.mainMenu = tkinter.Menu(self)
        self.tableMenu = tkinter.Menu(self.mainMenu)
        self.mainMenu.add_cascade(menu = self.tableMenu, label = "Меню")
        self.tableMenu.add_command(label = "Изменить форму таблицы", command = self.resizeTable, state = "disabled", font = "Helvetica 10")
        self.tableMenu.add_command(label = "Сохранить таблицу", command = self.saveTable, state = "disabled", font = "Helvetica 10")
        self.tableMenu.add_command(label = "Загрузить таблицу", command = self.loadTable, font = "Helvetica 10")
        self.tableMenu.add_command(label = "Загрузить сеанс", command = self.loadSession, font = "Helvetica 10")
        self["menu"] = self.mainMenu

    # простроить таблицу с исходными данными
    def constructGrid(self):
        self.startFrame.errorName.set("")
        self.startFrame.grid_remove()
        
        self.tableMenu.entryconfigure(0, state = "normal")
        self.tableMenu.entryconfigure(1, state = "normal")
        
        self.gridFrame.grid(row = 0, column = 0, sticky = ("N", "W", "E", "S"), ipadx = 15, ipady = 15)
        self.gridFrame.construct(self)
        self.gridFrame.display()
        
        self.s = ttk.Separator(self, orient = tkinter.VERTICAL)
        self.s.grid(row = 0, column = 1, sticky = ["N", "S"])
        
        self.settingsFrame.grid(row = 0, column = 2, sticky = ("N", "W", "E", "S"))
        self.settingsFrame.construct(self)
        self.adjustSize()

        self.constructed = True

    # перестроить таблицу с исходными данными (с изменением размера ок)
    def reconstructGrid(self):
        self.gridFrame.reconstruct(self)
        self.adjustSize()

    # определить новый размер таблицы
    def adjustSize(self):
        if (self.n0 < 9):
            width = self.n0 * 115 + 400
        else:
            width = 1435
        if (self.m0 < 16):
            height = self.m0 * 25 + 250
        else:
            height = 650
        self.geometry(f"{width}x{height}+100+100")
        self.gridFrame.canvas.xview_moveto(0);
        self.gridFrame.canvas.yview_moveto(0);

    # вызов окна изменения формы таблицы
    def resizeTable(self):
        ResizeWindow(self)
        return

    # читает введенные в таблицу данные и запускает решение
    def readTable(self):
        self.A = []
        for j in range(self.m0):
            self.A.append([])
            for i in range(self.n0):
                self.A[j].append(float(self.gridFrame.aCells[j][i].get()))
                
        self.b = []
        for j in range(self.m0):
            self.b.append(float(self.gridFrame.bCells[j].get()))

        self.c = []
        for i in range(self.n0):
            self.c.append(float(self.gridFrame.cCells[i].get()))

        self.constrSigns = []
        for j in range(self.m0):
            val = self.gridFrame.constrSignsCells[j].get()
            if val == ">=":
                self.constrSigns.append(1)
            elif val == "<=":
                self.constrSigns.append(-1)
            else:
                self.constrSigns.append(0)

        self.xSigns = []
        for i in range(self.n0):
            val = self.gridFrame.xSignsCells[i].get()
            if val == ">= 0":
                self.xSigns.append(1)
            elif val == "<= 0":
                self.xSigns.append(-1)
            else:
                self.xSigns.append(0)
        
        self.xInteger = []
        for i in range(self.n0):
            val = self.gridFrame.xIntegerCells[i].get()
            if val == "in Z":
                self.xInteger.append(1)
            else:
                self.xInteger.append(0)

        self.optimization = self.gridFrame.optimizationCell.get()
        self.solutionType = self.settingsFrame.solutionType.get()

        if self.solutionType == "simplexAuto":
            solver = AutoIntegerWrapper(self)
        elif self.solutionType == "simplexManual":
            solver = SimplexManualSolver(self)
            solver.parentInitialize(self)

    # сохраняет данные из таблицы в файл .tab
    def saveTable(self):
        fileToSave = tkinter.filedialog.asksaveasfile(mode='w', filetypes = [('Table file', '*.tab')], 
                                                      defaultextension = [('Table file', '*.tab')], initialdir = "./")
        if fileToSave is None:
            return

        fileToSave.write(str(self.m0) + "\n")
        fileToSave.write(str(self.n0) + "\n")
        vec = []
        for j in range(self.m0):
            vec = []
            for i in range(self.n0):
                vec.append(self.gridFrame.aCells[j][i].get())
            fileToSave.write(",".join(vec) + "\n")
                
        vec = []
        for j in range(self.m0):
            vec.append(self.gridFrame.bCells[j].get())
        fileToSave.write(",".join(vec) + "\n")

        vec = []
        for i in range(self.n0):
            vec.append(self.gridFrame.cCells[i].get())
        fileToSave.write(",".join(vec) + "\n")

        vec = []
        for j in range(self.m0):
            val = self.gridFrame.constrSignsCells[j].get()
            if val == ">=":
                vec.append("1")
            elif val == "<=":
                vec.append("-1")
            else:
                vec.append("0")
        fileToSave.write(",".join(vec) + "\n")

        vec = []
        for i in range(self.n0):
            val = self.gridFrame.xSignsCells[i].get()
            if val == ">= 0":
                vec.append("1")
            elif val == "<= 0":
                vec.append("-1")
            else:
                vec.append("0")
        fileToSave.write(",".join(vec) + "\n")

        vec = []
        for i in range(self.n0):
            val = self.gridFrame.xIntegerCells[i].get()
            if val == "in Z":
                vec.append("1")
            else:
                vec.append("0")
        fileToSave.write(",".join(vec) + "\n")
        
        fileToSave.write(self.gridFrame.optimizationCell.get() + "\n")
        fileToSave.write(self.settingsFrame.solutionType.get() + "\n")

        fileToSave.close()

    # загружает таблицу по заданному адресу .tab
    def loadTable(self):
        fileToLoad = tkinter.filedialog.askopenfile(mode ='r', filetypes = [('Table file', '*.tab')], 
                                                        defaultextension = [('Table file', '*.tab')], initialdir = "./")
        if fileToLoad is None:
            return
        content = fileToLoad.read()
        contentByLines = content.split("\n")

        self.m0 = int(contentByLines[0])
        self.n0 = int(contentByLines[1])

        if self.constructed:
            self.gridFrame.reconstruct(self)
        else:
            self.constructGrid()
            self.constructed = True

        for j in range(self.m0):
            vec = contentByLines[j + 2].split(',')
            for i in range(self.n0):

                self.gridFrame.aCells[j][i].set(vec[i])

        vec = contentByLines[self.m0 + 2].split(',')
        for j in range(self.m0):
            self.gridFrame.bCells[j].set(vec[j])

        vec = contentByLines[self.m0 + 3].split(',')
        for i in range(self.n0):
            self.gridFrame.cCells[i].set(vec[i])

        vec = contentByLines[self.m0 + 4].split(',')
        for j in range(self.m0):
            if vec[j] == "1":
                self.gridFrame.constrSignsCells[j].set(">=")
            elif vec[j] == "-1":
                self.gridFrame.constrSignsCells[j].set("<=")
            else:
                self.gridFrame.constrSignsCells[j].set("==")

        vec = contentByLines[self.m0 + 5].split(',')
        for i in range(self.n0):
            if vec[i] == "1":
                self.gridFrame.xSignsCells[i].set(">= 0")
            elif vec[i] == "-1":
                self.gridFrame.xSignsCells[i].set("<= 0")
            else:
                self.gridFrame.xSignsCells[i].set("в R")
        
        vec = contentByLines[self.m0 + 6].split(',')
        for i in range(self.n0):
            if vec[i] == "1":
                self.gridFrame.xIntegerCells[i].set("in Z")
            else:
                self.gridFrame.xIntegerCells[i].set("in R")
        self.gridFrame.display()
        self.gridFrame.optimizationCell.set(contentByLines[self.m0 + 7])
        self.settingsFrame.solutionType.set(contentByLines[self.m0 + 8])
        self.adjustSize()

        fileToLoad.close()
    
    # загрузка ручного симплекс-метода
    def loadSession(self):
        solver = SimplexManualSolver(self)
        solver.sessionInitialize()

# стартовое окно для ввода размерности задачи
class StartFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.resizeFrame = ttk.Frame(self)
        self.resizeFrame.grid_rowconfigure(0, weight = 1)
        self.resizeFrame.grid_rowconfigure(1, weight = 1)
        self.resizeFrame.grid_rowconfigure(2, weight = 1)
        self.resizeFrame.grid_rowconfigure(3, weight = 1)
        self.resizeFrame.grid_rowconfigure(4, weight = 3)
        self.resizeFrame.grid_rowconfigure(5, weight = 1)
        self.resizeFrame.grid_columnconfigure(0, weight = 1)
        self.resizeFrame.grid_columnconfigure(1, weight = 1)
        self.resizeFrame.grid(row = 0, column = 0, sticky = ("N", "W", "E", "S"), padx = 40, pady = 20)
        ttk.Label(self.resizeFrame, text = f"Задача условной оптимизации", font = "Helvetica 20 bold").grid(row = 0, column = 0, columnspan = 2, pady = 15, padx = 15)
        ttk.Label(self.resizeFrame, text = f"Задайте размерность задачи:", font = "Helvetica 12").grid(row = 1, column = 0, columnspan = 2, pady = 15, padx = 15)

        ttk.Label(self.resizeFrame, text = "Количество ограничений =", font = "Helvetica 12").grid(row = 2, column = 0, pady = 5, padx = 15)
        self.m0 = tkinter.StringVar()
        ttk.Entry(self.resizeFrame, textvariable = self.m0, font = "Helvetica 12").grid(row = 2, column = 1, pady = 5, padx = 5)
        ttk.Label(self.resizeFrame, text = "Количество переменных =", font = "Helvetica 12").grid(row = 3, column = 0, pady = 5, padx = 15)
        self.n0 = tkinter.StringVar()
        ttk.Entry(self.resizeFrame, textvariable = self.n0, font = "Helvetica 12").grid(row = 3, column = 1, pady = 5, padx = 5)
        
        self.continueButton = ttk.Button(self.resizeFrame, text = f"Продолжить", style = "my.TButton", command = lambda: self.continueCommand(parent))
        self.continueButton.grid(row = 4, column = 0, columnspan = 2, pady = 15, padx = 15, ipadx = 5, ipady = 5)

        self.errorName = tkinter.StringVar()
        self.errorLabel = ttk.Label(self.resizeFrame, textvariable = self.errorName, font = "Helvetica 12 bold").grid(row = 5, column = 0, columnspan = 2, pady = 10, padx = 15)

    # проверяет корректность данных
    def continueCommand(self, parent):
        valid = True
        m0Val = self.m0.get()
        n0Val = self.n0.get()
        try:
            if (int(m0Val) <= 0 or (int(m0Val) != float(m0Val))
            or int(n0Val) <= 0 or (int(n0Val) != float(n0Val))):
                self.errorName.set("Количество ограничений и количество переменных \nдолжны быть целыми положительными числами")
                valid = False
        except:
            self.errorName.set("Количество ограничений и количество переменных \nдолжны быть целыми положительными числами")
            valid = False
        if valid:
            self.errorName.set("")
            parent.m0 = int(m0Val)
            parent.n0 = int(n0Val)
            self.grid_remove()
            parent.constructGrid()

# окно для изменения размерности задачи
class ResizeWindow(tkinter.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.tk.call("tk", "windowingsystem")
        self.option_add("*tearOff", tkinter.FALSE)

        self.resizeFrame = ttk.Frame(self)
        self.resizeFrame.grid_rowconfigure(0, weight = 1)
        self.resizeFrame.grid_rowconfigure(1, weight = 1)
        self.resizeFrame.grid_rowconfigure(2, weight = 1)
        self.resizeFrame.grid_rowconfigure(3, weight = 3)
        self.resizeFrame.grid_rowconfigure(4, weight = 1)
        self.resizeFrame.grid_columnconfigure(0, weight = 1)
        self.resizeFrame.grid_columnconfigure(1, weight = 1)
        self.resizeFrame.grid(row = 0, column = 0, sticky = ("N", "W", "E", "S"), padx = 40, pady = 20)
        ttk.Label(self.resizeFrame, text = f"Введите количество ограничений и количество переменных:", font = "Helvetica 12").grid(row = 0, column = 0, columnspan = 2, pady = 15, padx = 15)

        ttk.Label(self.resizeFrame, text = "Количество ограничений =", font = "Helvetica 12").grid(row = 1, column = 0, pady = 5, padx = 15)
        self.m0 = tkinter.StringVar()
        ttk.Entry(self.resizeFrame, textvariable = self.m0, font = "Helvetica 12").grid(row = 1, column = 1, pady = 5, padx = 5)
        ttk.Label(self.resizeFrame, text = "Количество переменных =", font = "Helvetica 12").grid(row = 2, column = 0, pady = 5, padx = 15)
        self.n0 = tkinter.StringVar()
        ttk.Entry(self.resizeFrame, textvariable = self.n0, font = "Helvetica 12").grid(row = 2, column = 1, pady = 5, padx = 5)
        
        self.continueButton = ttk.Button(self.resizeFrame, text = f"Продолжить", style = "my.TButton", command = lambda: self.continueCommand(parent))
        self.continueButton.grid(row = 3, column = 0, columnspan = 2, pady = 15, padx = 15)

        self.errorName = tkinter.StringVar()
        self.errorLabel = ttk.Label(self.resizeFrame, textvariable = self.errorName, font = "Helvetica 12 bold").grid(row = 4, column = 0, columnspan = 2, pady = 10, padx = 15)

    # проверяет новую размерность задачи, вызывает перестройку главного окна
    def continueCommand(self, parent):
        valid = True
        m0Val = self.m0.get()
        n0Val = self.n0.get()
        try:
            if (int(m0Val) <= 0 or (int(m0Val) != float(m0Val))
            or int(n0Val) <= 0 or (int(n0Val) != float(n0Val))):
                self.errorName.set("Количество ограничений и количество переменных \nдолжны быть целыми положительными числами")
                valid = False
        except:
            self.errorName.set("Количество ограничений и количество переменных \nдолжны быть целыми положительными числами")
            valid = False
        if valid:
            self.errorName.set("")
            parent.m0 = int(m0Val)
            parent.n0 = int(n0Val)
            parent.gridFrame.reconstruct(parent)
            parent.gridFrame.display()
            parent.adjustSize()
            
            self.destroy()

# таблица, в которую вводятся данные
class GridFrame(DoubleScrolledFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.displayed = False

    # строит пустую таблицу. Не выводится на экран
    def construct(self, parent):
        self.m0 = parent.m0
        self.n0 = parent.n0

        #Objective function
        self.cCells = []
        self.optimizationCell = tkinter.StringVar()
        self.optimizationCell.set("max")
        for i in range(self.n0):
            self.cCells.append(tkinter.StringVar())

        #constaints
        self.aCells = []
        for j in range(self.m0):
            self.aCells.append([])
            for i in range(self.n0):
                self.aCells[j].append(tkinter.StringVar())

        #constrSigns                   
        self.constrSignsCells = []
        for j in range(self.m0):
            self.constrSignsCells.append(tkinter.StringVar(value = ">="))

        #Right-hand values
        self.bCells = []    
        for j in range(self.m0):
            self.bCells.append(tkinter.StringVar())
        
        #xSigns
        self.xSignsCells = []
        for i in range(self.n0):
            self.xSignsCells.append(tkinter.StringVar(value = ">= 0"))
        
        #xInteger
        self.xIntegerCells = []
        for i in range(self.n0):
            self.xIntegerCells.append(tkinter.StringVar(value = "in R"))    
    
    # перестраивает таблицу. Если размерность уменьшается - данные теряются.
    def reconstruct(self, parent):
        prevm = self.m0
        prevn = self.n0
        newm = parent.m0
        newn = parent.n0

        if newm >= prevm:
            for j in range(newm - prevm):
                self.bCells.append(tkinter.StringVar())
                self.constrSignsCells.append(tkinter.StringVar(value = ">="))
                self.aCells.append([])
                for i in range(prevn):
                    self.aCells[-1].append(tkinter.StringVar())
        else:
            for j in range(prevm - newm):
                self.bCells.pop()
                self.aCells.pop()
                self.constrSignsCells.pop()

        if newn >= prevn:
            for i in range(newn - prevn):
                self.cCells.append(tkinter.StringVar())
                self.xSignsCells.append(tkinter.StringVar(value = ">= 0"))
                self.xIntegerCells.append(tkinter.StringVar(value = "in R"))
                for j in range(newm):
                    self.aCells[j].append(tkinter.StringVar())
        else:
            for i in range(prevn - newn):
                self.cCells.pop()
                self.xSignsCells.pop()
                self.xIntegerCells.pop()
                for j in range(newm):
                    self.aCells[j].pop()
        
        self.m0 = newm
        self.n0 = newn

    # выводит таблицу на экран
    def display(self):
        if self.displayed:
            self.innerFrame.grid_remove()
        self.displayed = True
        self.innerFrame = ttk.Frame(self)
        self.innerFrame.grid()
        ttk.Label(self.innerFrame, text = "f = ", font = "Helvetica 12").grid(row = 0, column = 0, pady = 15, padx = (15, 0))
        ttk.Button(self.innerFrame, textvariable = self.optimizationCell, style = "my.TButton", width = 5, command = self.changeOptimizationType).grid(row = 0, column = self.n0 * 2 + 1, pady = 15, padx = (5, 0))
        
        for i in range(self.n0):
            ttk.Entry(self.innerFrame, textvariable = self.cCells[i], font = "Helvetica 12", width = 5).grid(row = 0, column = i * 2 + 1, pady = 15, padx = (5, 0))
            if i != self.n0 - 1:
                ttk.Label(self.innerFrame, text = f"x{i+1}  +", font = "Helvetica 12").grid(row = 0, column = i * 2 + 2, pady = 15, padx = (5, 0))
            else:
                ttk.Label(self.innerFrame, text = f"x{i+1}", font = "Helvetica 12").grid(row = 0, column = i * 2 + 2, pady = 15, padx = (5, 0))

        for j in range(self.m0):
            for i in range(self.n0):
                if i == 0:
                    ttk.Entry(self.innerFrame, textvariable = self.aCells[j][i], font = "Helvetica 12", width = 5).grid(row = j+1, column = i * 2, padx = (15, 0))
                else:
                    ttk.Entry(self.innerFrame, textvariable = self.aCells[j][i], font = "Helvetica 12", width = 5).grid(row = j+1, column = i * 2, padx = (5, 0))
                if i != self.n0 - 1:
                    ttk.Label(self.innerFrame, text = f"x{i+1} +", font = "Helvetica 12").grid(row = j+1, column = i * 2 + 1, padx = (5, 0))
                else:
                    ttk.Label(self.innerFrame, text = f"x{i+1}", font = "Helvetica 12").grid(row = j+1, column = i * 2 + 1, padx = (5, 0))

        for j in range(self.m0):
            ttk.Button(self.innerFrame, textvariable = self.constrSignsCells[j], style = "my.TButton", width = 3, command = lambda j0 = j: self.changeConstrSign(j0)).grid(row = j + 1, column = self.n0 * 2, padx = 5)
   
        for j in range(self.m0):
            ttk.Entry(self.innerFrame, textvariable = self.bCells[j], font = "Helvetica 12", width = 5).grid(row = j + 1, column = self.n0 * 2 + 1, padx = (5, 0))

        for i in range(self.n0):
            if i != 0:
                ttk.Label(self.innerFrame, text = f", x{i+1}", font = "Helvetica 12", width = 5).grid(row = self.m0 + 2, column = i * 2, pady = (15, 0), padx = (5, 0))
            else:
                ttk.Label(self.innerFrame, text = f" x{i+1}", font = "Helvetica 12", width = 5).grid(row = self.m0 + 2, column = i * 2, pady = (15, 0), padx = (5, 0))    
            ttk.Button(self.innerFrame, textvariable = self.xSignsCells[i], style = "my.TButton", width = 5, command = lambda i0 = i: self.changeXSign(i0)).grid(row = self.m0 + 2, column = i * 2 + 1, pady = (15, 0))
            ttk.Button(self.innerFrame, textvariable = self.xIntegerCells[i], style = "my.TButton", width = 5, command = lambda i0 = i: self.changeInteger(i0)).grid(row = self.m0 + 3, column = i * 2 + 1, pady = (15, 0))
            
    def changeOptimizationType(self):
        if self.optimizationCell.get() == "max":
            self.optimizationCell.set("min")
        elif self.optimizationCell.get() == "min":
            self.optimizationCell.set("max")

    def changeConstrSign(self, j):
        if self.constrSignsCells[j].get() == ">=":
            self.constrSignsCells[j].set("<=")
        elif self.constrSignsCells[j].get() == "<=":
            self.constrSignsCells[j].set("==")
        else:
            self.constrSignsCells[j].set(">=")
            
    def changeXSign(self, i):
        if self.xSignsCells[i].get() == ">= 0":
            self.xSignsCells[i].set("<= 0")
        elif self.xSignsCells[i].get() == "<= 0":
            self.xSignsCells[i].set("в R")
        else:
            self.xSignsCells[i].set(">= 0")
            
    def changeInteger(self, i):
        if self.xIntegerCells[i].get() == "in R":
            self.xIntegerCells[i].set("in Z")
        else:
            self.xIntegerCells[i].set("in R")

# окно правее таблицы, выбор метода оптимизации и начало оптимизации                
class SettingsFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

    def construct(self, parent):
        ttk.Button(self, text = "Начать оптимизацию", style = "my.TButton", command = parent.readTable).grid(row = 0, column = 0, pady = 15, padx = 10, ipadx = 5, ipady = 5)
        
        ttk.Label(self, text = "Симплекс метод", font = "Helvetica 12 bold").grid(row = 1, column = 0, pady = (10, 3), padx = 10)
        self.solutionType = tkinter.StringVar(value = "simplexAuto")
        self.autoButton = ttk.Radiobutton(self, text = "Автоматическое решение", variable = self.solutionType, value = "simplexAuto", style = "my.TRadiobutton")
        self.autoButton.grid(row = 2, column = 0, padx = 10)
        self.manualButton = ttk.Radiobutton(self, text = "Поэтапное решение", variable = self.solutionType, value = "simplexManual", style = "my.TRadiobutton")
        self.manualButton.grid(row = 3, column = 0, padx = 10)

# решение симплекс-методом без отображения промежуточных таблиц
#ДОДЕЛАТЬ ВЫВОД ЧЕРЕЗ ЦЕЛОЧИСЛЕННОЕ, СДЕЛАТЬ НОВЫЙ ОБЪЕКТ ДЛЯ ОТЧЕТОВ
    
# решение симплекс-методом с отображением промежуточных таблиц
class SimplexManualSolver(tkinter.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.grid_columnconfigure(0, weight = 1)
        self.grid_rowconfigure(2, weight = 1)
        self.tk.call("tk", "windowingsystem")
        self.option_add("*tearOff", tkinter.FALSE)
        self._zeroI = 10**-10

        self.mainMenu = tkinter.Menu(self)
        self.solverMenu = tkinter.Menu(self.mainMenu)
        self.mainMenu.add_cascade(menu = self.solverMenu, label = "Меню")
        self.solverMenu.add_command(label = "Сохранить сеанс", command = self.saveSession)
        self["menu"] = self.mainMenu

    # вызов стандартизации и подготовка к запуску
    def parentInitialize(self, parent):
        self.A = self.copyMatrix(parent.A)    
        self.b = self.copyVector(parent.b)
        self.c = self.copyVector(parent.c)
        self.c0 = self.copyVector(parent.c)
        self.constrSigns = self.copyVector(parent.constrSigns)
        self.xSigns = self.copyVector(parent.xSigns)
        self.optimization = parent.optimization

        self.state = []
        self.state.append(dict())
        self.state[0]["A"] = self.copyMatrix(self.A)
        self.currentState = 0
        self.finishState = -1
        self.standState = -1
        self.finishType = ""

        self.standardize()

    # загрузка сохраненной сессии
    def sessionInitialize(self):
        self.withdraw()
        fileToLoad = tkinter.filedialog.askopenfile(mode ='r', filetypes = [('Session file', '*.ses')], 
                                                        defaultextension = [('Session file', '*.ses')], initialdir = "./")
        if fileToLoad is None:
            self.destroy()
            return

        self.state("normal")
        self.lift()
        content = fileToLoad.read()
        contentByLines = content.split("\n")

        self.optimization = contentByLines[0]
        m = int(contentByLines[1])
        self.c = list(map(float, contentByLines[2].split(",")))
        self.cU = list(map(float, contentByLines[3].split(",")))
        self.uNum = int(contentByLines[4])
        self.currentState = int(contentByLines[5])
        self.finishState = int(contentByLines[6])
        self.standState = int(contentByLines[7])

        self.state = []
        stateNum = int(contentByLines[8])
        for k in range(stateNum):
            self.state.append(dict())
            self.state[k]["cBeta"] = list(map(float, contentByLines[9 + k * (m + 8)].split(",")))
            self.state[k]["beta"] = list(map(int, contentByLines[10 + k * (m + 8)].split(",")))
            self.state[k]["x"] = list(map(float, contentByLines[11 + k * (m + 8)].split(",")))
            self.state[k]["A"] = []
            for j in range(m):
                self.state[k]["A"].append([])
                self.state[k]["A"][j] = list(map(float, contentByLines[12 + j + k * (m + 8)].split(",")))
            self.state[k]["alpha"] = list(map(float, contentByLines[12 + m + k * (m + 8)].split(",")))
            self.state[k]["f"] = float(contentByLines[13 + m + k * (m + 8)])
            self.state[k]["delta"] = list(map(float, contentByLines[14 + m + k * (m + 8)].split(",")))
            self.state[k]["epsilon"] = int(contentByLines[15 + m + k * (m + 8)])
            self.state[k]["theta"] = int(contentByLines[16 + m + k * (m + 8)])

        self.rules = []
        self.finishType = contentByLines[9 + stateNum * (m + 8)]
        n = int(contentByLines[10 + stateNum * (m + 8)])
        for i in range(n):
            self.rules.append([])
            rulesForI = contentByLines[11 + i + stateNum * (m + 8)].split(",")
            for oneRule in rulesForI:
                coef, ind = oneRule.split(";")
                self.rules[i].append([float(coef), int(ind)])

        self.c0 = list(map(float, contentByLines[11 + n + stateNum * (m + 8)].split(",")))
        self.xLabels = contentByLines[12 + n + stateNum * (m + 8)].split(",")

        fileToLoad.close()

        if self.standState == -1 or self.currentState < self.standState:
            self.tableFrameInitialize(True)
        else:
            self.tableFrameInitialize(False)
        self.labelFrame = ttk.Frame(self)
        self.labelFrame.grid_columnconfigure(0, weight = 1)
        self.labelFrame.grid_rowconfigure(0, weight = 1)
        self.fLabel = tkinter.StringVar()
        ttk.Label(self.labelFrame, textvariable = self.fLabel, font = "Helvetica 10").grid()
        self.labelFrame.grid(row = 1, column = 0, sticky = ["N", "S", "W", "E"])
        self.topFrameInitialize()
        if self.standState == -1 or self.currentState < self.standState:
            self.stateDisplay(True)
        else:
            self.stateDisplay(False)

        if self.currentState >= 1:
            self.prevButton.state(["!disabled"])

        if self.finishState != -1 and self.currentState == self.finishState:
            self.finishButton.grid(row = 0, column = 2)
        elif self.standState != -1 and self.currentState >= self.standState:
            self.nextButton.grid(row = 0, column = 2)
        else:
            self.standardNextButton.grid(row = 0, column = 2)

    # стандартизация данных
    def standardize(self):
        curSt = self.currentState
        m, n = len(self.state[curSt]["A"]), len(self.state[curSt]["A"][0])
        self.state[curSt]["x"] = [0.0] * n

        self.rules = []
        self.xLabels = []
        for i in range(n):
            self.rules.append([[1, i]])
            self.xLabels.append(f"x{i+1}")

        for j in range(m):
            if self.b[j] < 0:
                self.b[j] = -self.b[j]
                for i in range(n):
                    self.state[curSt]["A"][j][i] = -self.state[curSt]["A"][j][i]
                self.constrSigns[j] = -self.constrSigns[j]

        for i in range(n):
            if self.xSigns[i] == -1:
                self.c[i] = -self.c[i]
                self.xLabels[i] = "~" + self.xLabels[i]
                for k in range(len(self.rules[i])):
                    self.rules[i][k][0] = -self.rules[i][k][0]
                for j in range(m):
                    self.state[curSt]["A"][j][i] = -self.state[curSt]["A"][j][i]
            elif self.xSigns[i] == 0:
                self.state[curSt]["x"].append(0)
                self.rules[i].append([-1, len(self.c)])
                self.xLabels.append(self.xLabels[i] + "\"")
                self.xLabels[i] = self.xLabels[i] + "'"
                self.c.append(-self.c[i])
                for j in range(m):
                    self.state[curSt]["A"][j].append(-self.state[curSt]["A"][j][i])
        
        dopVar = 0
        for j in range(m):
            if self.constrSigns[j] == 1:
                dopVar += 1
                self.state[curSt]["x"].append(0)
                self.xLabels.append(f"s{dopVar}")
                self.c.append(0)
                for j2 in range(m):
                    if j != j2:
                        self.state[curSt]["A"][j2].append(0)
                    else:
                        self.state[curSt]["A"][j2].append(-1)
            elif self.constrSigns[j] == -1:
                dopVar += 1
                self.state[curSt]["x"].append(0)
                self.xLabels.append(f"s{dopVar}")
                self.c.append(0)
                for j2 in range(m):
                    if j != j2:
                        self.state[curSt]["A"][j2].append(0)
                    else:
                        self.state[curSt]["A"][j2].append(1)

        self.basisPartition()
        self.uNum = 0
        self.cU = [0.0] * len(self.c)
        for j in range(m):
            if self.state[curSt]["beta"][j] == -1:
                self.uNum += 1
                self.state[curSt]["beta"][j] = len(self.state[curSt]["x"])
                self.state[curSt]["x"].append(self.b[j])
                self.xLabels.append(f"u{self.uNum}")
                self.cU.append(1.0)
                for j2 in range(m):
                    if j != j2:
                        self.state[curSt]["A"][j2].append(0)
                    else:
                        self.state[curSt]["A"][j2].append(1)
            else:
                self.state[curSt]["x"][self.state[curSt]["beta"][j]] = self.b[j]

        if self.uNum != 0:
            try:
                if not self.simplexIteration(self.cU, "min", 0):
                    self.state[self.currentState]["theta"] = -1
                    self.state.append(dict())
                    self.standState = self.currentState + 1
                    self.state[self.standState]["x"] = self.copyVector(self.state[self.currentState]["x"])
                    self.state[self.standState]["beta"] = self.copyVector(self.state[self.currentState]["beta"])
                    self.state[self.standState]["A"] = self.copyMatrix(self.state[self.currentState]["A"])
                    self.currentState += 1
                    try:
                        if not self.simplexIteration(self.c, self.optimization, self.uNum):
                            self.finishState = self.currentState
                            self.finishType = "linopt"
                    except:
                        self.finishState = self.currentState
                        self.finishType = "inf"
                    finally:
                        self.currentState -= 1
            except:
                self.finishState = self.currentState
                self.finishType = "no solution"
        else:
            self.standState = self.currentState
            try:
                if not self.simplexIteration(self.c, self.optimization, self.uNum):
                    self.finishState = self.currentState
                    self.finishType = "linopt"
            except:
                self.finishState = self.currentState
                self.finishType = "inf"
        
        if self.standState != -1:
            self.tableFrameInitialize(False)
        else:
            self.tableFrameInitialize(True)

        self.labelFrame = ttk.Frame(self)
        self.labelFrame.grid_columnconfigure(0, weight = 1)
        self.labelFrame.grid_rowconfigure(0, weight = 1)
        self.fLabel = tkinter.StringVar()
        ttk.Label(self.labelFrame, textvariable = self.fLabel, font = "Helvetica 10").grid()
        self.labelFrame.grid(row = 1, column = 0, sticky = ["N", "S", "W", "E"], ipadx = 10)
        self.topFrameInitialize()

        if self.finishState != -1:
            self.finishButton.grid(row = 0, column = 2)
            self.stateDisplay(False)
        elif self.standState != -1:
            self.nextButton.grid(row = 0, column = 2)
            self.stateDisplay(False)
        else:
            self.standardNextButton.grid(row = 0, column = 2)
            self.stateDisplay(True)

    # ?
    def basisPartition(self):
        curSt = self.currentState
        m, n = len(self.state[curSt]["A"]), len(self.state[curSt]["A"][0])
        self.state[curSt]["beta"] = [-1] * m
        for i in range(n):
            potInd = -1
            base = True
            for j in range(m):
                if self.equals(self.state[curSt]["A"][j][i], 1):
                    if potInd == -1:
                        potInd = j
                    else:
                        base = False
                        break
                elif not self.equals(self.state[curSt]["A"][j][i], 0):
                    base = False
                    break
            if base:
                self.state[curSt]["beta"][potInd] = i

    # полная симплекс-итерация
    def simplexIteration(self, c, optMethod, uNum):
        curSt = self.currentState
        m, n = len(self.state[curSt]["A"]), len(self.state[curSt]["A"][0]) - uNum

        self.state[curSt]["f"] = 0.0
        for i in range(n):
            self.state[curSt]["f"] += c[i] * self.state[curSt]["x"][i]

        self.state[curSt]["cBeta"] = []
        for j in range(m):
            if self.state[curSt]["beta"][j] < n:
                self.state[curSt]["cBeta"].append(c[self.state[curSt]["beta"][j]])
            else:
                self.state[curSt]["cBeta"].append(0)

        self.state[curSt]["delta"] = [0.0] * n
        for i in range(n):
            if i not in self.state[curSt]["beta"]:
                self.state[curSt]["delta"][i] = -c[i]
                for j in range(m):
                    self.state[curSt]["delta"][i] += self.state[curSt]["cBeta"][j] * self.state[curSt]["A"][j][i]

        for i in range(uNum):
            self.state[curSt]["delta"].append(0)
            for j in range(m):
                self.state[curSt]["delta"][n + i] += self.state[curSt]["cBeta"][j] * self.state[curSt]["A"][j][n + i]

        self.selectEpsilon(optMethod, uNum)
        eps = self.state[curSt]["epsilon"]
        self.state[curSt]["alpha"] = [-1.0] * m
        self.state[curSt]["theta"] = -1

        if eps != -1:
            for j in range(m):
                if self.more(self.state[curSt]["A"][j][eps], 0):
                    self.state[curSt]["alpha"][j] = self.state[curSt]["x"][self.state[curSt]["beta"][j]] / self.state[curSt]["A"][j][eps]

            self.selectTheta()
            assert self.state[curSt]["theta"] != -1, "Function unbounded"

            return True
        else:
            return False

    # построение новой таблицы
    def newState(self):
        curSt = self.currentState
        newSt = self.currentState + 1

        self.state.append(dict())
        self.state[newSt]["A"] = self.copyMatrix(self.state[curSt]["A"])
        self.state[newSt]["x"] = self.copyVector(self.state[curSt]["x"])
        self.state[newSt]["beta"] = self.copyVector(self.state[curSt]["beta"])

        m, n = len(self.state[newSt]["A"]), len(self.state[newSt]["A"][0])
        epsilon = self.state[curSt]["epsilon"]
        theta = self.state[curSt]["theta"]

        pivot = self.state[newSt]["A"][theta][epsilon]
        self.state[newSt]["x"][self.state[newSt]["beta"][theta]] /= pivot
        for i in range(n):
            self.state[newSt]["A"][theta][i] /= pivot

        for j in range(m):
            if j != theta:
                pivot = self.state[newSt]["A"][j][epsilon]
                self.state[newSt]["x"][self.state[newSt]["beta"][j]] -= self.state[newSt]["x"][self.state[newSt]["beta"][theta]] * pivot
                for i in range(n):
                    self.state[newSt]["A"][j][i] -= self.state[newSt]["A"][theta][i] * pivot
        self.state[newSt]["x"][epsilon] = self.state[newSt]["x"][self.state[newSt]["beta"][theta]]
        self.state[newSt]["x"][self.state[newSt]["beta"][theta]] = 0
        self.state[newSt]["beta"][theta] = self.state[curSt]["epsilon"]

        self.currentState += 1

    # выбор, какую переменную убрать из базиса
    def selectEpsilon(self, optMethod, uNum):
        curSt = self.currentState
        potentialEpsilons = []
        if optMethod == "max":
            for i in range(len(self.state[curSt]["delta"]) - uNum):
                if self.less(self.state[curSt]["delta"][i], 0):
                    potentialEpsilons.append(i)
        else:
            for i in range(len(self.state[curSt]["delta"]) - uNum):
                if self.more(self.state[curSt]["delta"][i], 0):
                    potentialEpsilons.append(i)
        if len(potentialEpsilons) != 0:
            self.state[curSt]["epsilon"] = random.choice(potentialEpsilons)
        else:
            self.state[curSt]["epsilon"] = -1

    # Выбор, какую переменную добавить в базис
    def selectTheta(self):
        curSt = self.currentState
        alphaVal = float("inf")
        self.state[curSt]["theta"] = -1
        for j in range(len(self.state[curSt]["alpha"])):
            if not self.less(self.state[curSt]["alpha"][j], 0) and self.less(self.state[curSt]["alpha"][j], alphaVal):
                self.state[curSt]["theta"] = j
                alphaVal = self.state[curSt]["alpha"][j]

    def less(self, val1, val2):
        return val2 - val1 > self._zeroI

    def equals(self, val1, val2):
        return abs(val2 - val1) < self._zeroI

    def more(self, val1, val2):
        return val1 - val2 > self._zeroI

    def copyVector(self, vector):
        res = vector[::]
        return res

    def copyMatrix(self, matrix):
        res = [[]] * len(matrix)
        for i in range(len(matrix)):
            res[i] = matrix[i][::]
        return res

    def stringVector(self, vector, floatValues = True):
        if floatValues:
            strVec = [f"{elem:{6}.{2}f}" for elem in vector]
        else:
            strVec = [f"{elem + 1}" for elem in vector]
        return "[" + ", ".join(strVec) + "]"

    # построение рамки, в которой будет отображаться рамка симлекс-таблицы и рамка с кнопками смены таблицы
    def topFrameInitialize(self):
        self.topFrame = ttk.Frame(self)
        self.topFrame.grid(row = 0, column = 0, sticky = ["N", "E", "W", "S"], ipadx = 10, ipady = 7)
        self.topFrame.grid_columnconfigure(0, weight = 1)
        self.topFrame.grid_columnconfigure(1, weight = 1)
        self.topFrame.grid_columnconfigure(2, weight = 1)

        self.prevButton = ttk.Button(self.topFrame, text = "Назад", command = self.prevTable)
        self.prevButton.grid(row = 0, column = 0)
        self.prevButton.state(["disabled"])
        self.stateLabel = tkinter.StringVar()
        ttk.Label(self.topFrame, textvariable = self.stateLabel, font = "Helvetica 10").grid(row = 0, column = 1)
        self.standardNextButton = ttk.Button(self.topFrame, text = "Далее", command = self.standardNextTable)
        self.nextButton = ttk.Button(self.topFrame, text = "Далее", command = self.nextTable)
        self.finishButton = ttk.Button(self.topFrame, text = "Завершить", command = self.redirectReport)

    # построение рамки симплекс-таблицы
    def tableFrameInitialize(self, uShow):
        self.tableFrame = DoubleScrolledFrame(self)
        self.tableFrame.grid(row = 2, column = 0, sticky = ["N", "E", "W", "S"])
        curSt = self.currentState
        m = len(self.state[curSt]["A"])
        self.prevEps = -1
        self.prevThet = -1

        if uShow:
            n = len(self.state[curSt]["A"][0])
        else:
            n = len(self.state[curSt]["A"][0]) - self.uNum

        ttk.Label(self.tableFrame, text = "cBeta", font = "Helvetica 10").grid(row = 1, column = 0, padx = (10, 5), pady = 5)
        ttk.Label(self.tableFrame, text = "beta", font = "Helvetica 10").grid(row = 1, column = 2, padx = (5, 5), pady = 5)
        ttk.Label(self.tableFrame, text = "xBeta", font = "Helvetica 10").grid(row = 1, column = 4, padx = (5, 5), pady = 5)
        for i in range(n):
            ttk.Label(self.tableFrame, text = self.xLabels[i], font = "Helvetica 10").grid(row = 1, column = i + 6, padx = (5, 5), pady = 5)
        ttk.Label(self.tableFrame, text = "alpha", font = "Helvetica 10").grid(row = 1, column = n + 7, padx = (5, 10), pady = 5)

        self.cBetaCells = []
        self.betaCells = []
        self.xBetaCells = []
        self.aCells = []
        self.aLabels = []
        self.alphaCells = []
        for j in range(m):
            jTransform = lambda j0 = j: j0
            self.cBetaCells.append(tkinter.StringVar())
            ttk.Label(self.tableFrame, textvariable = self.cBetaCells[jTransform()], font = "Helvetica 10").grid(row = j + 3, column = 0, padx = (10, 5), pady = 5)
            self.betaCells.append(tkinter.StringVar())
            ttk.Label(self.tableFrame, textvariable = self.betaCells[j], font = "Helvetica 10").grid(row = j + 3, column = 2, padx = (5, 5), pady = 5)
            self.xBetaCells.append(tkinter.StringVar())
            ttk.Label(self.tableFrame, textvariable = self.xBetaCells[j], font = "Helvetica 10").grid(row = j + 3, column = 4, padx = (5, 5), pady = 5)
            self.aCells.append([])
            self.aLabels.append([])
            for i in range(n):
                self.aCells[j].append(tkinter.StringVar())
                self.aLabels[j].append(ttk.Label(self.tableFrame, textvariable = self.aCells[j][i], font = "Helvetica 10"))
                self.aLabels[j][i].grid(row = j + 3, column = i + 6, padx = (5, 5), pady = 5)
            self.alphaCells.append(tkinter.StringVar())
            ttk.Label(self.tableFrame, textvariable = self.alphaCells[j], font = "Helvetica 10").grid(row = j + 3, column = n + 7, padx = (5, 10), pady = 5)
        
        self.fName = tkinter.StringVar(value = "f")
        ttk.Label(self.tableFrame, textvariable = self.fName, font = "Helvetica 10").grid(row = m + 4, column = 2, padx = (5, 5), pady = 5)
        self.fCell = tkinter.StringVar()
        ttk.Label(self.tableFrame, textvariable = self.fCell, font = "Helvetica 10").grid(row = m + 4, column = 4, padx = (5, 5), pady = 5)
        self.deltaCells = []
        for i in range(n):
            self.deltaCells.append(tkinter.StringVar())
            ttk.Label(self.tableFrame, textvariable = self.deltaCells[i], font = "Helvetica 10").grid(row = m + 4, column = i + 6, padx = (5, 5), pady = (5))

        for i in range(n + 8):
            ttk.Separator(self.tableFrame, orient = "horizontal").grid(row = 0, column = i, sticky = ["W", "E"])
            ttk.Separator(self.tableFrame, orient = "horizontal").grid(row = 2, column = i, sticky = ["W", "E"])
            ttk.Separator(self.tableFrame, orient = "horizontal").grid(row = m + 3, column = i, sticky = ["W", "E"])
        for j in range(m + 5):
            ttk.Separator(self.tableFrame, orient = "vertical").grid(row = j, column = 1, sticky = ["N", "S"])
            ttk.Separator(self.tableFrame, orient = "vertical").grid(row = j, column = 3, sticky = ["N", "S"])
            ttk.Separator(self.tableFrame, orient = "vertical").grid(row = j, column = 5, sticky = ["N", "S"])
            ttk.Separator(self.tableFrame, orient = "vertical").grid(row = j, column = n + 6, sticky = ["N", "S"])

    # переход к предыдущей симплекс-таблице
    def prevTable(self):
        self.currentState -= 1
        if self.currentState == self.finishState - 1:
            self.finishButton.grid_forget()
            if self.standState == self.finishState:
                self.tableFrame.grid_remove()
                self.tableFrameInitialize(True)
                self.standardNextButton.grid(row = 0, column = 2)
            else:
                self.nextButton.grid(row = 0, column = 2)
        elif self.currentState == self.standState - 1:
            self.tableFrame.grid_remove()
            self.tableFrameInitialize(True)
            self.nextButton.grid_forget()
            self.standardNextButton.grid(row = 0, column = 2)
        elif self.currentState == 0:
            self.prevButton.state(["disabled"])

        if self.standState != -1 and self.currentState >= self.standState:
            self.stateDisplay(False)
        else:
            self.stateDisplay(True)

    # переход к следующей симплекс-таблице
    def nextTable(self):
        if self.currentState == len(self.state) - 1:
            try:
                self.newState()
                if not self.simplexIteration(self.c, self.optimization, self.uNum):
                    self.state[self.currentState]["theta"] = -1
                    self.nextButton.grid_forget()
                    self.finishState = self.currentState
                    self.finishType = "linopt"
                    self.finishButton.grid(row = 0, column = 2)
            except:
                self.nextButton.grid_forget()
                self.finishState = self.currentState
                self.finishButton.grid(row = 0, column = 2)
                self.finishType = "inf"
        elif self.currentState == self.finishState - 1:
            self.nextButton.grid_forget()
            self.finishButton.grid(row = 0, column = 2)
            self.currentState += 1
        else:
            self.currentState += 1
        self.stateDisplay(False)

        if self.currentState >= 1:
            self.prevButton.state(["!disabled"])
    
    # переход к следующей симплекс-таблице (после завершения стандартизации)
    def standardNextTable(self):
        if self.currentState == len(self.state) - 1:
            try:
                self.newState()
                if not self.simplexIteration(self.cU, "min", 0):
                    if self.equals(self.state[self.currentState]["f"], 0):
                        self.state[self.currentState]["theta"] = -1
                        self.state.append(dict())
                        self.standState = self.currentState + 1
                        self.state[self.standState]["x"] = self.copyVector(self.state[self.currentState]["x"])
                        self.state[self.standState]["beta"] = self.copyVector(self.state[self.currentState]["beta"])
                        self.state[self.standState]["A"] = self.copyMatrix(self.state[self.currentState]["A"])
                        self.currentState += 1
                        try:
                            if not self.simplexIteration(self.c, self.optimization, self.uNum):
                                self.finishState = self.currentState
                                self.finishType = "linopt"
                        except:
                            self.finishState = self.currentState
                            self.finishType = "inf"
                        finally:
                            self.currentState -= 1
                    else:
                        self.standardNextButton.grid_forget()
                        self.finishState = self.currentState
                        self.finishButton.grid(row = 0, column = 2)
                        self.finishType = "no solution"
            except:
                self.standardNextButton.grid_forget()
                self.finishState = self.currentState
                self.finishButton.grid(row = 0, column = 2)
                self.finishType = "no solution"
        elif self.currentState == self.finishState - 1:
            self.standardNextButton.grid_forget()
            self.finishButton.grid(row = 0, column = 2)
            self.currentState += 1
            self.tableFrame.grid_remove()
            self.tableFrameInitialize(False)
        elif self.currentState == self.standState - 1:
            self.standardNextButton.grid_forget()
            self.nextButton.grid(row = 0, column = 2)
            self.currentState += 1
            self.tableFrame.grid_remove()
            self.tableFrameInitialize(False)
        else:
            self.currentState += 1
        
        if self.standState != -1 and self.currentState >= self.standState:
            self.stateDisplay(False)
        else:
            self.stateDisplay(True)

        if self.currentState >= 1:
            self.prevButton.state(["!disabled"])

    # отображение текущей таблицы
    def stateDisplay(self, uShow):
        curSt = self.currentState
        m = len(self.state[curSt]["A"])
        self.stateLabel.set(f"Итерация {self.currentState + 1}")

        if uShow:
            n = len(self.state[curSt]["A"][0])
            fStr = "F = "
            varList = []
            for i in range(self.uNum):
                varList.append(f"u{i + 1}")
            fStr += " + ".join(varList) + " -> min"
            self.fLabel.set(fStr)
            self.fName.set("F")
        else:
            n = len(self.state[curSt]["A"][0]) - self.uNum
            fStr = "f = "
            varList = []
            for i in range(n):
                if not self.equals(self.c[i], 0):
                    varList.append(f"{self.c[i]: .2f} * {self.xLabels[i]}")
            fStr += " + ".join(varList) + f" -> {self.optimization}"
            self.fLabel.set(fStr)
            self.fName.set("f")

        for j in range(m):
            self.cBetaCells[j].set(f"{self.state[curSt]['cBeta'][j]: .2f}")
            self.betaCells[j].set(f"{self.xLabels[self.state[curSt]['beta'][j]]}")
            self.xBetaCells[j].set(f"{self.state[curSt]['x'][self.state[curSt]['beta'][j]]: .2f}")
            for i in range(n):
                self.aCells[j][i].set(f"{self.state[curSt]['A'][j][i]: .2f}")
            self.alphaCells[j].set(f"{self.state[curSt]['alpha'][j]: .2f}")
        self.fCell.set(f"{self.state[curSt]['f']: .2f}")
        for i in range(n):
            self.deltaCells[i].set(f"{self.state[curSt]['delta'][i]: .2f}")

        if self.prevEps != -1 and self.prevThet != -1:
            self.aLabels[self.prevThet][self.prevEps].configure(font = "Helvetica 10")
            self.prevEps = -1
            self.prevThet = -1
        if self.state[curSt]['epsilon'] != -1 and self.state[curSt]['theta'] != -1:
            self.aLabels[self.state[curSt]['theta']][self.state[curSt]['epsilon']].configure(font = "Helvetica 11 bold")
            self.prevEps = self.state[curSt]['epsilon']
            self.prevThet = self.state[curSt]['theta']
    
    # сохранение текущей сессии
    def saveSession(self):
        fileToSave = tkinter.filedialog.asksaveasfile(mode='w', filetypes = [('Session file', '*.ses')], 
                                                      defaultextension = [('Session file', '*.ses')], initialdir = "./")
        if fileToSave is None:
            return

        fileToSave.write(str(self.optimization) + "\n")
        m = len(self.state[0]["A"])
        fileToSave.write(str(m) + "\n")
        fileToSave.write(",".join(list(map(str, self.c))) + "\n")
        fileToSave.write(",".join(list(map(str, self.cU))) + "\n")
        fileToSave.write(str(self.uNum) + "\n")
        fileToSave.write(str(self.currentState) + "\n")
        fileToSave.write(str(self.finishState) + "\n")
        fileToSave.write(str(self.standState) + "\n")

        fileToSave.write(str(len(self.state)) + "\n")
        for st in self.state:
            fileToSave.write(",".join(list(map(str, st["cBeta"]))) + "\n")
            fileToSave.write(",".join(list(map(str, st["beta"]))) + "\n")
            fileToSave.write(",".join(list(map(str, st["x"]))) + "\n")
            for j in range(m):
                fileToSave.write(",".join(list(map(str, st["A"][j]))) + "\n")
            fileToSave.write(",".join(list(map(str, st["alpha"]))) + "\n")
            fileToSave.write(str(st["f"]) + "\n")
            fileToSave.write(",".join(list(map(str, st["delta"]))) + "\n")
            fileToSave.write(str(st["epsilon"]) + "\n")
            fileToSave.write(str(st["theta"]) + "\n")
        
        fileToSave.write(self.finishType + "\n")
        n = len(self.rules)
        fileToSave.write(str(n) + "\n")
        for i in range(n):
            rulesForI = []
            for k in range(len(self.rules[i])):
                rulesForI.append(str(self.rules[i][k][0]) + ";" + str(self.rules[i][k][1]))
            fileToSave.write(",".join(rulesForI) + "\n")

        fileToSave.write(",".join(list(map(str, self.c0))) + "\n")
        fileToSave.write(",".join(list(map(str, self.xLabels))) + "\n")
        fileToSave.close()
        self.lift()

    # вызов отчета
    def redirectReport(self):
        SimplexReport(self)

# общий отчет о выполнении симлпекс-метода
class SimplexReport(tkinter.Toplevel):
    def __init__(self, parent, gridTo = None):
        if gridTo == None:
            super().__init__(parent)
        else:
            super().__init__(gridTo)

        self.mainFrame = DoubleScrolledFrame(self)
        self.mainFrame.grid(row = 0, column = 0, sticky = ("N", "S", "E", "W"))
        self.grid_rowconfigure(0, weight = 1)
        self.grid_columnconfigure(0, weight = 1)
        self.lift()
        self.postoptimized = False
        self.reportMenu = tkinter.Menu(self)
        self.reportMenuUnit = tkinter.Menu(self.reportMenu)
        self.reportMenu.add_cascade(menu = self.reportMenuUnit, label = "Меню", font = "Helvetica 12")
        self.reportMenuUnit.add_command(label = "Сохранить отчет", command = self.saveReport)
        self["menu"] = self.reportMenu

        self.reportFrame = ttk.Frame(self.mainFrame)
        self.reportFrame.grid(row = 0, column = 0)

        self.reportLines = []
        if parent and parent.finishType == "linopt":
            curSt = parent.currentState
            xOriginal = [0.0] * len(parent.rules)
            for i in range(len(parent.rules)):
                for k in range(len(parent.rules[i])):
                    xOriginal[i] += parent.state[parent.currentState]["x"][parent.rules[i][k][1]] * parent.rules[i][k][0]

            uNum = parent.uNum
            self.reportLines.append(f"Линейная оптимизация({parent.optimization})")
            self.reportLines.append(f"f ({parent.optimization}) = {parent.state[curSt]['f']:{6}.{2}f}")
            self.reportLines.append(f"x = {parent.stringVector(xOriginal)}")
            self.reportLines.append(f"c = {parent.stringVector(parent.c0)}")
            self.reportLines.append("A (финальная) = [")
            for j in range(len(parent.state[curSt]["A"]) - 1):
                self.reportLines.append(parent.stringVector(parent.state[curSt]["A"][j][:len(parent.state[curSt]["A"][j])-uNum]))
            self.reportLines.append(parent.stringVector(parent.state[curSt]["A"][len(parent.state[curSt]["A"]) - 1][:len(parent.state[curSt]["A"][len(parent.state[curSt]["A"]) - 1])-uNum]) + ']')
            xExtended = []
            for i in range(len(parent.state[curSt]['x'][:len(parent.state[curSt]['x'])-uNum])):
                xExtended.append(f"{parent.state[curSt]['x'][i]: .2f} {parent.xLabels[i]}")
            self.reportLines.append(f"x (расширенное) = [{', '.join(xExtended)}]")
            basisLabeled = []
            for j in range(len(parent.state[curSt]['beta'])):
                basisLabeled.append(parent.xLabels[parent.state[curSt]['beta'][j]])
            self.reportLines.append(f"Базис = [{', '.join(basisLabeled)}]")
            self.reportMenuUnit.add_command(label = "Постоптимизация", command = lambda: self.callPostoptWindow(parent), font = "Helvetica 10")
        elif parent and parent.finishType == "inf":
            self.reportLines.append(f"Линейная оптимизация({parent.optimization})")
            if parent.optimization == "max":
                self.reportLines.append(f"f ({parent.optimization}) = Положительная бесконечность")
            else:
                self.reportLines.append(f"f ({parent.optimization}) = Отрицательная бесконечность")
            self.reportLines.append(f"Значение функции не ограничено")
        else:
            self.reportLines.append(f"Значение функции не определено")
            self.reportLines.append(f"Область определения функции - пустое множество")

        for i in range(len(self.reportLines)):
            if i == 0:
                ttk.Label(self.reportFrame, text = self.reportLines[i], font = "Helvetica 12").grid(padx = 10, pady = (10, 0))
            elif i < len(self.reportLines) - 1:
                ttk.Label(self.reportFrame, text = self.reportLines[i], font = "Helvetica 12").grid(padx = 10)
            else:
                ttk.Label(self.reportFrame, text = self.reportLines[i], font = "Helvetica 12").grid(padx = 10, pady = (0, 10))

    def saveReport(self):
        fileToSave = tkinter.filedialog.asksaveasfile(mode='w', filetypes = [('Text file', '*.txt')], 
                                                      defaultextension = [('Text file', '*.txt')], initialdir = "./")
        if fileToSave is None:
            return

        fileToSave.write("Отчет линейной оптимизации:\n\n")
        for i in range(len(self.reportLines)):
            fileToSave.write(self.reportLines[i] + "\n")

        if self.postoptimized == True:
            fileToSave.write("\n\nОтчет постоптимизации:\n\n")
            for i in range(len(self.postoptReportLines)):
                fileToSave.write(self.postoptReportLines[i] + "\n")
        fileToSave.close()

    def callPostoptWindow(self, parent):
        postoptInitWindow(self, parent)

    def postoptimize(self, parent, cChange, bChange):
        fSt = parent.finishState
        m, n = len(parent.state[fSt]["A"]), len(parent.state[fSt]["A"][0]) - parent.uNum

        self.bChange = bChange
        self.cChange = []
        for i in range(n + parent.uNum):
            self.cChange.append(0)
        for i in range(len(parent.rules)):
           for k in range(len(parent.rules[i])):
               self.cChange[parent.rules[i][k][1]] += cChange[i] * parent.rules[i][k][0]

        self.omegaUpper = float("inf")
        self.omegaLower = float("-inf")

        basis0 = sorted(parent.state[0]["beta"])

        self.xOmega = [0.0 for _ in range(n)]
        #b change
        for j in range(m):
            coef = 0
            for j2 in range(m):
                coef += parent.state[fSt]["A"][j][basis0[j2]] * self.bChange[j2]
            if coef == 0:
                continue
            self.xOmega[parent.state[fSt]["beta"][j]] = coef
            omegaVal = -parent.state[fSt]["x"][parent.state[fSt]["beta"][j]] / coef
            if coef > 0:
                self.omegaLower = max(self.omegaLower, omegaVal)
            else:
                self.omegaUpper = min(self.omegaUpper, omegaVal)

        #c change
        for i in range(n):
            if i not in parent.state[fSt]["beta"]:
                coef = -self.cChange[i]
                for j in range(m):
                    coef += self.cChange[parent.state[fSt]["beta"][j]] * parent.state[fSt]["A"][j][i]
                if coef == 0:
                    continue
                omegaVal = -parent.state[fSt]["delta"][i] / coef
                if omegaVal < 0:
                    self.omegaLower = max(self.omegaLower, omegaVal)
                else:
                    self.omegaUpper = min(self.omegaUpper, omegaVal)

        #f value
        self.fOmega = [0.0, 0.0, 0.0]       
        for i in range(n):
            self.fOmega[0] += parent.c[i] * parent.state[fSt]["x"][i]
        for j in range(m):
            self.fOmega[1] += parent.state[fSt]["delta"][basis0[j]] * self.bChange[j] + self.cChange[parent.state[fSt]["beta"][j]] * parent.state[fSt]["x"][parent.state[fSt]["beta"][j]]
            rowValue = 0.0
            for j2 in range(m):
                rowValue += parent.state[fSt]["A"][j][basis0[j2]] * self.bChange[j2]
            self.fOmega[2] += self.cChange[parent.state[fSt]["beta"][j]] * rowValue

        #print postoptimization report
        if self.postoptimized == True:
            self.postoptFrame.destroy()

        self.postoptFrame = ttk.Frame(self.mainFrame)
        self.postoptFrame.grid(row = 1, column = 0)

        self.postoptReportLines = []
        self.postoptReportLines.append(f"Постоптимизация")
        self.postoptReportLines.append(f"f (w) = {self.fOmega[0]: .{2}f} + {self.fOmega[1]: .{2}f} * w + {self.fOmega[2]: .{2}f} * w ^ 2")
        xExtended = [f"({parent.state[fSt]['x'][i]: .{2}f} + {self.xOmega[i]: .{2}f}w){parent.xLabels[i]}" for i in range(n)]
        self.postoptReportLines.append(f"x (w) = [{', '.join(xExtended)}]")
        self.postoptReportLines.append(f"Для параметра w в интервале [{self.omegaLower: .{2}f}, {self.omegaUpper: .{2}f}]")
        self.postoptReportLines.append(f"Вектор изменения целевой функции = w * {cChange}")
        self.postoptReportLines.append(f"Вектор изменения значений правой части = w * {bChange}")

        for i in range(len(self.postoptReportLines)):
            if i == 0:
                ttk.Label(self.postoptFrame, text = self.postoptReportLines[i], font = "Helvetica 12").grid(padx = 10, pady = (10, 0))
            elif i < len(self.postoptReportLines) - 1:
                ttk.Label(self.postoptFrame, text = self.postoptReportLines[i], font = "Helvetica 12").grid(padx = 10)
            else:
                ttk.Label(self.postoptFrame, text = self.postoptReportLines[i], font = "Helvetica 12").grid(padx = 10, pady = (0, 10))

        self.postoptimized = True

# постоптимизация
class postoptInitWindow(tkinter.Toplevel):
    def __init__(self, parent, dataSource):
        super().__init__(parent)
        self.postInitFrame = DoubleScrolledFrame(self)
        self.postInitFrame.grid_rowconfigure(0, weight = 1)
        self.postInitFrame.grid_rowconfigure(1, weight = 1)
        self.postInitFrame.grid_rowconfigure(2, weight = 1)
        self.postInitFrame.grid_rowconfigure(3, weight = 3)
        self.postInitFrame.grid_rowconfigure(4, weight = 1)
        self.postInitFrame.grid_columnconfigure(0, weight = 1)
        self.postInitFrame.grid_columnconfigure(1, weight = 1)
        self.postInitFrame.grid(row = 0, column = 0, sticky = ["N", "S", "W", "E"], padx = 40, pady = 20)

        m = len(dataSource.state[dataSource.finishState]["A"])
        n = len(dataSource.rules)
        maxlen = max(m, n)
        ttk.Label(self.postInitFrame, text = f"Введите векторы изменения целевой функции\nи значений правой части", font = "Helvetica 12").grid(row = 0, column = 0, columnspan = maxlen + 3, pady = 10, padx = 10)
        ttk.Label(self.postInitFrame, text = "Вектор изменения целевой функции:", font = "Helvetica 12").grid(row = 1, column = 0, columnspan = 3, pady = 5, padx = 10)
        ttk.Label(self.postInitFrame, text = "Вектор изменения значений правой части:", font = "Helvetica 12").grid(row = 2, column = 0, columnspan = 3, pady = 5, padx = 10)

        self.cChangeCells = []
        for i in range(n):
            self.cChangeCells.append(tkinter.StringVar(value = 0))
        self.bChangeCells = []
        for j in range(m):
            self.bChangeCells.append(tkinter.StringVar(value = 0))
        
        for i in range(n):
            ttk.Entry(self.postInitFrame, textvariable = self.cChangeCells[i], font = "Helvetica 12", width = 5).grid(row = 1, column = 3 + i, pady = 5, padx = (0, 10))

        for j in range(m):
            ttk.Entry(self.postInitFrame, textvariable = self.bChangeCells[j], font = "Helvetica 12", width = 5).grid(row = 2, column = 3 + j, pady = 5, padx = (0, 10))

        self.startButton = ttk.Button(self.postInitFrame, text = f"Продолжить", style = "my.TButton", command = lambda: self.startPostopt(parent, dataSource))
        self.startButton.grid(row = 3, column = (maxlen - 1) // 2, columnspan = 2, pady = 5, padx = 10)

        self.errorName = tkinter.StringVar()
        ttk.Label(self.postInitFrame, textvariable = self.errorName, font = "Helvetica 12").grid(row = 4, column = 0, columnspan = maxlen + 3, pady = (0, 10), padx = 10)

    def startPostopt(self, parent, dataSource):
        valid = True
        cChange = []
        bChange=  []
        m, n = len(self.bChangeCells), len(self.cChangeCells)
        try:
            for i in range(n):
                cChange.append(float(self.cChangeCells[i].get()))
            for j in range(m):
                bChange.append(float(self.bChangeCells[j].get()))
        except:
            self.errorName.set("Значения векторов должны быть неотрицательными числами")
            valid = False
        if valid:
            self.errorName.set("")
            parent.postoptimize(dataSource, cChange, bChange)
            self.destroy()

class AutoSimplexReport(tkinter.Toplevel):
    def __init__(self, parent, finishType, optimization, c, c0, x, rules, A0, b0, gridTo = None):
        if gridTo == None:
            super().__init__(parent)
        else:
            super().__init__(gridTo)

        self.mainFrame = DoubleScrolledFrame(self)
        self.mainFrame.grid(row = 0, column = 0, sticky = ("N", "S", "E", "W"))
        self.grid_rowconfigure(0, weight = 1)
        self.grid_columnconfigure(0, weight = 1)
        self.lift()
        self.reportMenu = tkinter.Menu(self)
        self.reportMenuUnit = tkinter.Menu(self.reportMenu)
        self.reportMenu.add_cascade(menu = self.reportMenuUnit, label = "Меню", font = "Helvetica 12")
        self.reportMenuUnit.add_command(label = "Сохранить отчет", command = self.saveReport)
        self["menu"] = self.reportMenu

        self.reportFrame = ttk.Frame(self.mainFrame)
        self.reportFrame.grid(row = 0, column = 0)

        self.reportLines = []
        if finishType == "linopt":
            xOriginal = numpy.array([0.0 for _ in range(max(rules, key = lambda val: val[1])[1] + 1)])
            for new, orig, sign in rules:
                xOriginal[orig] += x[new] * sign
            if optimization == "max":
                c = -c

            self.reportLines.append(f"Линейная оптимизация({optimization})")
            self.reportLines.append(f"f ({optimization}) = {c @ x:.{3}f}")
            self.reportLines.append(f"x = [{', '.join([str(elem) for elem in numpy.around(xOriginal, 3)])}]")
            self.reportLines.append(f"c = [{', '.join([str(elem) for elem in numpy.around(c0, 3)])}]")
            
            A0 = numpy.array(A0)
            b0 = numpy.array(b0)
            print(A0.shape, xOriginal.shape, b0.shape)
            s = numpy.around((b0 - A0 @ xOriginal), 3)
            self.reportLines.append(f"s (остатки) = [{', '.join([str(elem) for elem in s])}]")
        elif finishType == "inf":
            self.reportLines.append(f"Линейная оптимизация({parent.optimization})")
            if parent.optimization == "max":
                self.reportLines.append(f"f ({optimization}) = Положительная бесконечность")
            else:
                self.reportLines.append(f"f ({optimization}) = Отрицательная бесконечность")
            self.reportLines.append(f"Значение функции не ограничено")
        else:
            self.reportLines.append(f"Значение функции не определено")
            self.reportLines.append(f"Область определения функции - пустое множество")

        for i in range(len(self.reportLines)):
            if i == 0:
                ttk.Label(self.reportFrame, text = self.reportLines[i], font = "Helvetica 12").grid(padx = 10, pady = (10, 0))
            elif i < len(self.reportLines) - 1:
                ttk.Label(self.reportFrame, text = self.reportLines[i], font = "Helvetica 12").grid(padx = 10)
            else:
                ttk.Label(self.reportFrame, text = self.reportLines[i], font = "Helvetica 12").grid(padx = 10, pady = (0, 10))

    def saveReport(self):
        fileToSave = tkinter.filedialog.asksaveasfile(mode='w', filetypes = [('Text file', '*.txt')], 
                                                      defaultextension = [('Text file', '*.txt')], initialdir = "./")
        if fileToSave is None:
            return

        fileToSave.write("Отчет линейной оптимизации:\n\n")
        for i in range(len(self.reportLines)):
            fileToSave.write(self.reportLines[i] + "\n")

        if self.postoptimized == True:
            fileToSave.write("\n\nОтчет постоптимизации:\n\n")
            for i in range(len(self.postoptReportLines)):
                fileToSave.write(self.postoptReportLines[i] + "\n")
        fileToSave.close()

# симплекс-метод с целочисленностью
# Стандарт первую
# Cycle: solve, check INT and if there is better, separate into two, standartize two subtables.
class AutoIntegerWrapper():
    def __init__(self, parent):
        self.currentIterations = deque()
        
        self.A = copy.deepcopy(parent.A)   
        self.A0 = copy.deepcopy(parent.A)  
        self.b = copy.deepcopy(parent.b)
        self.b0 = copy.deepcopy(parent.b)
        self.c = copy.deepcopy(parent.c)
        self.c0 = copy.deepcopy(parent.c)
        self.constrSigns = copy.deepcopy(parent.constrSigns)
        self.xSigns = copy.deepcopy(parent.xSigns)
        self.xInteger = copy.deepcopy(parent.xInteger)
        print(self.xInteger)
        self.optimization = parent.optimization
        self.finishType = ""
        
        self.best_f = float("inf") 
        self.best_solution = None

        res = self.standardize()
        print(res)
        if not res:
            self.finishType = "no solution"
            AutoSimplexReport(parent, self.finishType, self.optimization, None, None, None, None, None, None)
            return 
        self.currentIterations.append((self.A, self.beta, self.betaX, self.c))
        
        self.finishType = "no solution"
        while (self.currentIterations and self.finishType != "inf"):
            self.compute()
        
        print("BEST SOLUTION", self.best_solution)
        print(self.finishType)
        if self.best_solution is None:
            AutoSimplexReport(parent, "no solution", self.optimization, None, None, None, None, None, None)
            return
        x = numpy.array([0.0 for _ in range(len(self.best_solution[3]))])
        for i in range(len(self.best_solution[2])):
            x[self.best_solution[2][i]] = self.best_solution[1][i]
        AutoSimplexReport(parent, self.finishType, self.optimization, self.best_solution[3], self.c0, x, self.rules, self.A0, self.b0)

    def compute(self):
        print("SUTATO")
        print("\n\n\n\n\n")
        res = self.solve(*self.currentIterations.popleft())
        if res == None:
            self.finishType = "inf"
            self.best_solution = (self.A, self.beta, self.betaX, self.c)
            return
        else:
            A, beta, betaX, c = res
            self.finishType = "linopt"    

        x = [0.0 for _ in range(len(c))]
        for i in range(len(betaX)):
            x[betaX[i]] = beta[i]
        xOrig = numpy.array([0.0 for _ in range(max(self.rules, key = lambda val: val[1])[1] + 1)])
        for new, orig, sign in self.rules:
            xOrig[orig] += x[new] * sign
        print("X", x)
        print("c", c)
        print("XORIG", xOrig)
        print("RULES", self.rules)
        f = c @ x
        print(xOrig, f)
        if f > self.best_f:
            return
        integerSolution = True
        integerInds = []
        for i in range(len(self.xInteger)):
            if self.xInteger[i] and not (math.isclose(xOrig[i] % 1, 0, abs_tol=1e-6) or math.isclose(1 - xOrig[i] % 1, 0, abs_tol=1e-6)):
                integerSolution = False
                integerInds.append(i)
        print("INTEGER SOLUTION", integerSolution)
        if integerSolution:
            if f < self.best_f:
                self.best_solution = copy.deepcopy((A, beta, betaX, c))
                self.best_f = f
        else:
            integerInd = random.choice(integerInds)
            xVal = xOrig[integerInd]
            A = numpy.pad(A, ((0, 1), (0, 0)), mode="constant", constant_values=0)
            beta = numpy.pad(beta, ((0, 1)), mode="constant", constant_values=0)
            Achanges = numpy.zeros(shape=(len(A[-1])))
            for new, orig, sign in self.rules:
                if orig == integerInd:
                    inds = numpy.where(numpy.isclose(A[:, new], 1, rtol=1e-6))
                    Achanges[new] += sign
                    print(inds)
                    if not len(inds[0]):
                        continue
                    betaInd = inds[0][0]
                    print(A[betaInd], A[-1])
                    Achanges -= A[betaInd] * sign
                    #A[-1, orig] += sign
                    #BETA >= 0?
                    beta[-1] -= beta[betaInd] * sign
            A[-1] = Achanges
            self.A = numpy.pad(A, ((0, 0), (0, 2)), mode="constant", constant_values=0)
            self.A[-1, -2] = 1  
            self.beta = copy.deepcopy(beta)
            self.beta[-1] += math.floor(xVal)
            self.c = numpy.pad(c, ((0, 1)), mode="constant", constant_values=0)
            self.betaX = numpy.pad(betaX, ((0, 1)), mode="constant", constant_values=0)
            if self.beta[-1] < 0:
                self.beta[-1] = -self.beta[-1]
                self.A[-1] = -self.A[-1]
            self.A[-1, -1] = 1
            self.betaX[-1] = self.A.shape[1] - 1
            self.cU = numpy.array([0.0 for _ in range(len(c) + 2)])
            self.cU[-1] = 1
            print(self.A, self.beta, self.betaX)
            res = self.solve(self.A, self.beta, self.betaX, self.cU, u = True)
            print("AFTER u removal")
            print(self.A, self.beta, self.betaX)
            if res == None or self.A.shape[1] - 1 in res[2]:
                print("NO SOLUTION LEFT")
            else:
                print(f"\n\nINTEGER {integerInd} <= {math.floor(xVal)}: {(res[0][:, :-1], res[1], res[2], self.c)}")
                self.currentIterations.append(copy.deepcopy((res[0][:, :-1], res[1], res[2], self.c)))

            self.A = numpy.pad(A, ((0, 0), (0, 2)), mode="constant", constant_values=0)
            self.A[-1, -2] = -1  
            self.beta = copy.deepcopy(beta)
            self.beta[-1] += math.ceil(xVal)
            self.c = numpy.pad(c, ((0, 1)), mode="constant", constant_values=0)
            self.betaX = numpy.pad(betaX, ((0, 1)), mode="constant", constant_values=0)
            if self.beta[-1] < 0:
                self.beta[-1] = -self.beta[-1]
                self.A[-1] = -self.A[-1]
            self.A[-1, -1] = 1
            self.betaX[-1] = self.A.shape[1] - 1
            self.cU = numpy.array([0.0 for _ in range(len(c) + 2)])
            self.cU[-1] = 1
            print(self.A, self.beta, self.betaX)
            res = self.solve(self.A, self.beta, self.betaX, self.cU, u = True)
            print("AFTER u removal")
            print(self.A, self.beta, self.betaX)
            if res == None or self.A.shape[1] - 1 in res[2]:
                print("NO SOLUTION RIGHT")
            else:
                print(f"\n\nINTEGER {integerInd} >= {math.ceil(xVal)}: {(res[0][:, :-1], res[1], res[2], self.c)}")
                self.currentIterations.append(copy.deepcopy((res[0][:, :-1], res[1], res[2], self.c)))
        
        # стандартизация исходной задачи
    def standardize(self):
        print("\n\nSTANDARDIZE")
        print("XSIGNS,", self.xSigns)
        m, n = len(self.A), len(self.A[0])

        if self.optimization != "min":
            self.c = [-elem for elem in self.c]

        self.rules = []
        for i in range(n):
            self.rules.append([i, i, 1])
        
        for j in range(m):
            if self.b[j] < 0:
                self.b[j] = -self.b[j]
                for i in range(n):
                    self.A[j][i] = -self.A[j][i]
                self.constrSigns[j] = -self.constrSigns[j]

        for i in range(n):
            if self.xSigns[i] == -1:
                self.c[i] = -self.c[i]
                for k in range(len(self.rules[i])):
                    self.rules[i][2] = -1
                for j in range(m):
                    self.A[j][i] = -self.A[j][i]
            elif self.xSigns[i] == 0:
                self.rules.append([len(self.c), i, -1])
                self.c.append(-self.c[i])
                for j in range(m):
                    self.A[j].append(-self.A[j][i])

        self.beta = [0 for _ in range(m)]
        self.betaX = [-1 for _ in range(m)]
        for j in range(m):
            if self.constrSigns[j] == 1:
                self.c.append(0)
                for j2 in range(m):
                    self.A[j2].append(0)
                self.A[j][-1] = -1
            elif self.constrSigns[j] == -1:
                self.c.append(0)
                self.beta[j] = self.b[j]
                self.betaX[j] = len(self.A[0])
                for j2 in range(m):
                    self.A[j2].append(0)
                self.A[j][-1] = 1
        
        print("A", self.A, "b", self.b, "c", self.c, "beta", self.beta, "betaX", self.betaX)
        uCount = 0
        self.cU = [0.0] * len(self.c)
        for j in range(m):
            if self.beta[j] == 0:
                found = False
                for i in range(len(self.c)):
                    if i not in self.betaX:
                        if math.isclose(self.A[j][i], 0, rel_tol=1e-6, abs_tol=1e-6) or self.A[j][i] < 0:
                            break
                        for j2 in range(m):
                            if not math.isclose(self.A[j2][i], 0, rel_tol=1e-6, abs_tol=1e-6):
                                break
                        else:
                            found = True
                            val = self.A[j][i]
                            for i2 in range(len(self.c)):
                                self.A[j][i2] /= val
                            self.b[j] /= val
                            self.betaX[j] = i
                            self.beta = self.b[j]
                            break
                if not found:
                    self.beta[j] = self.b[j]
                    self.betaX[j] = len(self.cU)
                    self.cU.append(1.0)
                    uCount += 1
                    for j2 in range(m):
                        self.A[j2].append(0)
                    self.A[j][-1] = 1
            
        self.A = numpy.array(self.A, dtype = "float32")
        self.beta = numpy.array(self.beta, dtype = "float32")
        self.c = numpy.array(self.c, dtype = "float32")
        self.cU = numpy.array(self.cU, dtype = "float32")
        print(self.A, self.beta, self.c, self.cU)
        if uCount != 0:
            res = self.solve(self.A, self.beta, self.betaX, self.cU, u = True)
            if res == None:
                print("RES = NONE")
                return False
            self.A, self.beta, self.betaX, self.cU = res
            self.x = numpy.array([0.0 for _ in range(len(self.A[0]))])
            for i in range(len(self.betaX)):
                self.x[self.betaX[i]] = self.beta[i]
            if not math.isclose(self.x[-uCount:].sum(), 0, rel_tol=1e-6, abs_tol=1e-6):
                print("x", self.x)
                print("RES COST != 0")
                return False
            self.A = self.A[:, :-uCount]
            self.x = self.x[:-uCount]
        return True
    
    def solve(self, A, beta, betaX, c, u = False):
        m, n = A.shape
        
        cBeta = numpy.array([c[betaX[j]] for j in range(m)])
        print("cBeta", cBeta)
        f = cBeta @ beta
        print("f", f)
        alpha = cBeta @ A - c
        print("alpha", alpha)
        uCount = 0
        if u:
            uCount = int(c.sum())
        
        while True:
            print("A", A, "beta", beta, "betaX", betaX, "c", c)
            print("cBeta", cBeta)
            print("f", f)
            print("alpha", alpha)
            
            forceU = False
            if u and math.isclose(f, 0, rel_tol=1e-6, abs_tol=1e-6):
                for i in range(n - uCount, n):
                    if i in betaX:
                        forceU = True
                        uInd = i
                        betaU = numpy.argwhere(betaX == uInd)[0, 0]
                        break
                if not forceU:
                    print("U SOLVED", (A, beta, betaX, c))
                    return (A, beta, betaX, c)

            alphaInds = list()
            #alphaIndsZeros = list()
            for i in range(n):
                if (alpha[i] > 0 and not math.isclose(alpha[i], 0, rel_tol=1e-6, abs_tol=1e-6)):
                    alphaInds.append(i)
                #elif math.isclose(alpha[i], 0) and i not in betaX:
                #    alphaIndsZeros.append(i)
            if alphaInds:
                alphaInd = random.choice(alphaInds)
            #elif alphaIndsZeros:
            #    alphaInd = random.choice(alphaIndsZeros)
            else:
                if forceU:
                    alphaInd = random.choice([i for i in range(n - uCount) if A[betaU, i] != 0])
                else:
                    return (A, beta, betaX, c)
            print("alphaInds", alphaInds)
            #print("alphaIndsZeros", alphaIndsZeros)
            print("alphaInd", alphaInd)
            betaInd = -1
            betaVal = math.inf
            for j in range(m):
                if A[j][alphaInd] > 0 and beta[j] / A[j][alphaInd] < betaVal:
                    betaInd = j
                    betaVal = beta[j] / A[j][alphaInd]
            if forceU:
                betaInd = betaU
            elif not u and betaInd == -1:
                return None
            print("betaInd", betaInd)
            beta[betaInd] /= A[betaInd, alphaInd]
            A[betaInd] /= A[betaInd, alphaInd]
            A[betaInd, alphaInd] = 0.0
            beta -=  A[:, alphaInd] * beta[betaInd]
            print("dA", A[:, alphaInd].reshape(m, 1) @ A[betaInd].reshape(1, n))
            A -= A[:, alphaInd].reshape(m, 1) @ A[betaInd].reshape(1, n)
            alpha -= A[betaInd] * alpha[alphaInd]
            cBeta[betaInd] = c[alphaInd]
            betaX[betaInd] = alphaInd
            f = cBeta @ beta
            A[:, alphaInd] = 0.0
            alpha[alphaInd] = 0.0
            A[betaInd, alphaInd] = 1.0
            
            forceU = False
            if u and math.isclose(f, 0, rel_tol=1e-6, abs_tol=1e-6):
                for i in range(n - uCount, n):
                    if i in betaX:
                        forceU = True
                        uInd = i
                        betaU = numpy.argwhere(betaX == uInd)[0, 0]
                        break
                if not forceU:
                    print("U SOLVED", (A, beta, betaX, c))
                    return (A, beta, betaX, c)
            

if __name__ == "__main__":

    LinOptSolv = LinearOptimizationSolver()
    LinOptSolv.mainloop()
    
