from __future__ import division
from Tkinter import *
import tkMessageBox
from PIL import Image, ImageTk
import ttk
import os
import glob
import random
import xml.etree.ElementTree as ET
import lxml.etree as etree

# colors for the bboxes
COLORS = ['red', 'blue', 'olive', 'teal', 'cyan', 'green', 'black']
# image sizes for the examples
SIZE = 2000, 500

class LabelTool():
	def __init__(self, master):
		# set up the main frame
		self.parent = master
		self.parent.title("LabelTool")
		self.frame = Frame(self.parent)
		self.frame.pack(fill=BOTH, expand=1)
		self.parent.resizable(width = FALSE, height = FALSE)

		# initialize global state
		self.imageDir = ''
		self.imageList= []
		self.egDir = ''
		self.egList = []
		self.outDir = ''
		self.cur = 0
		self.total = 0
		self.category = 0
		self.imagename = ''
		self.labelfilename = ''
		self.tkimg = None
		self.currentLabelclass = ''
		self.cla_can_temp = []
		self.classcandidate_filename = 'class.txt'

		# initialize mouse state
		self.STATE = {}
		self.STATE['click'] = 0
		self.STATE['x'], self.STATE['y'] = 0, 0

		# reference to bbox
		self.bboxIdList = []
		self.bboxId = None
		self.bboxList = []
		self.hl = None
		self.vl = None



		# main panel for labeling
		self.mainPanel = Canvas(self.frame, cursor='tcross')
		self.mainPanel.bind("<Button-1>", self.mouseClick)
		self.mainPanel.bind("<Motion>", self.mouseMove)
		self.parent.bind("<Escape>", self.cancelBBox)  # press <Espace> to cancel current bbox
		self.parent.bind("s", self.cancelBBox)
		self.parent.bind("a", self.prevImage) # press 'a' to go backforward
		self.parent.bind("d", self.nextImage) # press 'd' to go forward
		self.mainPanel.grid(row = 1, column = 1, rowspan = 4, sticky = W+N)

		# choose class
		self.classname = StringVar()
		self.classcandidate = ttk.Combobox(self.frame,state='readonly',textvariable=self.classname)
		self.classcandidate.grid(row=1,column=2)
		if os.path.exists(self.classcandidate_filename):
			with open(self.classcandidate_filename) as cf:
				for line in cf.readlines():
					# print line
					self.cla_can_temp.append(line.strip('\n'))
		#print self.cla_can_temp
		self.classcandidate['values'] = self.cla_can_temp
		self.classcandidate.current(0)
		self.currentLabelclass = self.classcandidate.get() #init
		self.btnclass = Button(self.frame, text = 'Load Class', command = self.setClass)
		self.btnclass.grid(row=2,column=2,sticky = W+E)

		# showing bbox info & delete bbox
		self.lb1 = Label(self.frame, text = 'Bounding boxes:')
		self.lb1.grid(row = 3, column = 2,  sticky = W+N)
		self.listbox = Listbox(self.frame, width = 22, height = 12)
		self.listbox.grid(row = 4, column = 2, sticky = N+S)
		self.btnDel = Button(self.frame, text = 'Delete', command = self.delBBox)
		self.btnDel.grid(row = 5, column = 2, sticky = W+E+N)
		self.btnClear = Button(self.frame, text = 'ClearAll', command = self.clearBBox)
		self.btnClear.grid(row = 6, column = 2, sticky = W+E+N)

		# control panel for image navigation
		self.ctrPanel = Frame(self.frame)
		self.ctrPanel.grid(row = 7, column = 1, columnspan = 2, sticky = W+E)
		self.prevBtn = Button(self.ctrPanel, text='<< Prev', width = 10, command = self.prevImage)
		self.prevBtn.pack(side = LEFT, padx = 5, pady = 3)
		self.nextBtn = Button(self.ctrPanel, text='Next >>', width = 10, command = self.nextImage)
		self.nextBtn.pack(side = LEFT, padx = 5, pady = 3)
		self.progLabel = Label(self.ctrPanel, text = "Progress:     /    ")
		self.progLabel.pack(side = LEFT, padx = 5)
		self.tmpLabel = Label(self.ctrPanel, text = "Go to Image No.")
		self.tmpLabel.pack(side = LEFT, padx = 5)
		self.idxEntry = Entry(self.ctrPanel, width = 5)
		self.idxEntry.pack(side = LEFT)
		self.goBtn = Button(self.ctrPanel, text = 'Go', command = self.gotoImage)
		self.goBtn.pack(side = LEFT)

		# display mouse position
		self.disp = Label(self.ctrPanel, text='')
		self.disp.pack(side = RIGHT)

		self.frame.columnconfigure(1, weight = 1)
		self.frame.rowconfigure(4, weight = 1)

		# for debugging
##        self.setImage()
##        self.loadDir()

	def loadDir(self, dbg = False):
		self.cur = 1
		self.total = len(self.imageList)
		self.loadImage()
		

	def loadImage(self):
		# load image
		imagepath = self.imageList[self.cur - 1]
		self.img = Image.open(imagepath)
		self.tkimg = ImageTk.PhotoImage(self.img)
		self.mainPanel.config(width = max(self.tkimg.width(), 400), height = max(self.tkimg.height(), 400))
		self.mainPanel.create_image(0, 0, image = self.tkimg, anchor=NW)
		self.progLabel.config(text = "%04d/%04d" %(self.cur, self.total))

		# load labels
		self.clearBBox()
		self.imagename = os.path.split(imagepath)[-1].split('.')[0]
		labelname = self.imagename + '.txt'
		self.labelfilename = os.path.join(self.outDir, labelname)
		bbox_cnt = 0
		if os.path.exists(self.labelfilename):
			with open(self.labelfilename) as f:
				for (i, line) in enumerate(f):
					if i == 0:
						bbox_cnt = int(line.strip())
						continue
					# tmp = [int(t.strip()) for t in line.split()]
					tmp = line.split()
					#print tmp
					self.bboxList.append(tuple(tmp))
					tmpId = self.mainPanel.create_rectangle(int(tmp[0]), int(tmp[1]), \
															int(tmp[2]), int(tmp[3]), \
															width = 2, \
															outline = COLORS[(len(self.bboxList)-1) % len(COLORS)])
					# print tmpId
					self.bboxIdList.append(tmpId)
					self.listbox.insert(END, '%s : (%d, %d) -> (%d, %d)' %(tmp[4],int(tmp[0]), int(tmp[1]), \
																	  int(tmp[2]), int(tmp[3])))
					self.listbox.itemconfig(len(self.bboxIdList) - 1, fg = COLORS[(len(self.bboxIdList) - 1) % len(COLORS)])

	def saveImage(self):
		root = ET.Element('annotation')
		f = ET.SubElement(root, 'folder')
		f.text = "VOC2007"
		fn = ET.SubElement(root, 'filename')
		fn.text = '{}.jpg'.format(self.imagename)
		seg = ET.SubElement(root, 'segmented')
		seg.text = '0'
		size = ET.SubElement(root, 'size')
		w = ET.SubElement(size, 'width')
		w.text = '2000'
		h = ET.SubElement(size, 'height')
		h.text = '500'
		d = ET.SubElement(size, 'depth')
		d.text = '1'
		for bbox in self.bboxList:
			o = ET.SubElement(root, 'object')
			name = ET.SubElement(o, 'name')
			name.text = bbox[4]
			pose = ET.SubElement(o, 'pose')
			pose.text = 'Unspecified'
			trunc = ET.SubElement(o, 'truncated')
			trunc.text = '0'
			diff = ET.SubElement(o, 'difficult')
			diff.text = '0'
			bndbox = ET.SubElement(o, 'bndbox')
			xmin = ET.SubElement(bndbox, 'xmin')
			xmin.text = str(bbox[0])
			ymin = ET.SubElement(bndbox, 'ymin')
			ymin.text = str(bbox[1])
			xmax = ET.SubElement(bndbox, 'xmax')
			xmax.text = str(bbox[2])
			ymax = ET.SubElement(bndbox, 'ymax')
			ymax.text = str(bbox[3])
		tree = ET.ElementTree(root)
		fic= '{}/VOC2007/Annotations/{}.xml'.format(os.getcwd(), self.imagename)
		tree.write(fic)
		x = etree.parse(fic)
		with open(fic,'w') as f: 
			f.write(etree.tostring(x, pretty_print = True))
		fn = '{}{}.png'.format(self.imageDir[:-1], self.imagename)
		im = Image.open(fn)
		rgb_im = im.convert('RGB')
		rgb_im.save('VOC2007/JPEGImages/{}.jpg'.format(self.imagename))


	def mouseClick(self, event):
		if self.STATE['click'] == 0:
			self.STATE['x'], self.STATE['y'] = event.x, event.y
		else:
			x1, x2 = min(self.STATE['x'], event.x), max(self.STATE['x'], event.x)
			y1, y2 = min(self.STATE['y'], event.y), max(self.STATE['y'], event.y)
			self.bboxList.append((x1, y1, x2, y2, self.currentLabelclass))
			self.bboxIdList.append(self.bboxId)
			self.bboxId = None
			self.listbox.insert(END, '%s : (%d, %d) -> (%d, %d)' %(self.currentLabelclass,x1, y1, x2, y2))
			self.listbox.itemconfig(len(self.bboxIdList) - 1, fg = COLORS[(len(self.bboxIdList) - 1) % len(COLORS)])
		self.STATE['click'] = 1 - self.STATE['click']

	def mouseMove(self, event):
		self.disp.config(text = 'x: %d, y: %d' %(event.x, event.y))
		if self.tkimg:
			if self.hl:
				self.mainPanel.delete(self.hl)
			self.hl = self.mainPanel.create_line(0, event.y, self.tkimg.width(), event.y, width = 2)
			if self.vl:
				self.mainPanel.delete(self.vl)
			self.vl = self.mainPanel.create_line(event.x, 0, event.x, self.tkimg.height(), width = 2)
		if 1 == self.STATE['click']:
			if self.bboxId:
				self.mainPanel.delete(self.bboxId)
			self.bboxId = self.mainPanel.create_rectangle(self.STATE['x'], self.STATE['y'], \
															event.x, event.y, \
															width = 2, \
															outline = COLORS[len(self.bboxList) % len(COLORS)])

	def cancelBBox(self, event):
		if 1 == self.STATE['click']:
			if self.bboxId:
				self.mainPanel.delete(self.bboxId)
				self.bboxId = None
				self.STATE['click'] = 0

	def delBBox(self):
		sel = self.listbox.curselection()
		if len(sel) != 1 :
			return
		idx = int(sel[0])
		self.mainPanel.delete(self.bboxIdList[idx])
		self.bboxIdList.pop(idx)
		self.bboxList.pop(idx)
		self.listbox.delete(idx)

	def clearBBox(self):
		for idx in range(len(self.bboxIdList)):
			self.mainPanel.delete(self.bboxIdList[idx])
		self.listbox.delete(0, len(self.bboxList))
		self.bboxIdList = []
		self.bboxList = []

	def prevImage(self, event = None):
		self.saveImage()
		if self.cur > 1:
			self.cur -= 1
			self.loadImage()

	def nextImage(self, event = None):
		self.saveImage()
		if self.cur < self.total:
			self.cur += 1
			self.loadImage() 

	def gotoImage(self):
		idx = int(self.idxEntry.get())
		if 1 <= idx and idx <= self.total:
			self.saveImage()
			self.cur = idx
			self.loadImage()

	def setClass(self):
		self.currentLabelclass = self.classcandidate.get()
		print 'set label class to :',self.currentLabelclass
		self.imageDir = '{}/Images/{}/*'.format(os.getcwd(), self.currentLabelclass)
		#print self.imageDir 
		#print self.category
		self.imageList = glob.glob(self.imageDir)
		self.loadDir()

##    def setImage(self, imagepath = r'test2.png'):
##        self.img = Image.open(imagepath)
##        self.tkimg = ImageTk.PhotoImage(self.img)
##        self.mainPanel.config(width = self.tkimg.width())
##        self.mainPanel.config(height = self.tkimg.height())
##        self.mainPanel.create_image(0, 0, image = self.tkimg, anchor=NW)

if __name__ == '__main__':
	root = Tk()
	tool = LabelTool(root)
	root.resizable(width =  True, height = True)
	root.mainloop()
