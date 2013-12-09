
import pyximport; pyximport.install()

import cython_mmc


from random import *
import random as pyrandom
pyrandom.seed(200)
#from numpy import *
import numpy as np

from rlscore import data_sources
from rlscore.learner.abstract_learner import AbstractSvdLearner
from rlscore.learner.abstract_learner import AbstractIterativeLearner

class InteractiveRlsClassifier(AbstractSvdLearner, AbstractIterativeLearner):
    
    
    def loadResources(self):
        AbstractSvdLearner.loadResources(self)
        AbstractIterativeLearner.loadResources(self)
        
        self.constraint = 0
        if not self.resource_pool.has_key('number_of_clusters'):
            raise Exception("Parameter 'number_of_clusters' must be given.")
        self.labelcount = int(self.resource_pool['number_of_clusters'])
        
        if self.labelcount == 2:
            self.oneclass = True
        else:
            self.oneclass = False
        
        '''
        if self.resource_pool.has_key(data_sources.TRAIN_LABELS):
            Y_orig = self.resource_pool[data_sources.TRAIN_LABELS]
            if Y_orig.shape[1] == 1:
                self.Y = mat(zeros((Y_orig.shape[0], 2)))
                self.Y[:, 0] = Y_orig
                self.Y[:, 1] = - Y_orig
                self.oneclass = True
            else:
                self.Y = Y_orig.copy()
                self.oneclass = False
            for i in range(self.Y.shape[0]):
                largestind = 0
                largestval = self.Y[i, 0]
                for j in range(self.Y.shape[1]):
                    if self.Y[i, j] > largestval:
                        largestind = j
                        largestval = self.Y[i, j]
                    self.Y[i, j] = -1.
                self.Y[i, largestind] = 1.
        else:
            size = self.svecs.shape[0]
            ysize = self.labelcount
            if self.labelcount == None: self.labelcount = 2
            self.Y = RandomLabelSource(size, ysize).readLabels()
        '''
        if not self.resource_pool.has_key(data_sources.TRAIN_LABELS):
            raise Exception
        
        self.classvec = self.resource_pool[data_sources.TRAIN_LABELS]
        self.size = self.classvec.shape[0]
        self.Y = -np.ones((self.size, self.labelcount))
        self.classcounts = np.zeros((self.labelcount), dtype = np.int32)
        for i in range(self.size):
            clazzind = self.classvec[i]
            self.Y[i, clazzind] = 1
            self.classcounts[clazzind] = self.classcounts[clazzind] + 1
        
        
        #self.labelcount = self.Y.shape[1]
        
        self.svecs_list = []
        for i in range(self.size):
            self.svecs_list.append(self.svecs[i].T)
        
        self.fixedindices = []
        if self.resource_pool.has_key('fixed_indices'):
            self.fixedindices = self.resource_pool['fixed_indices']
             
    
    def train(self):
        regparam = float(self.resource_pool[data_sources.TIKHONOV_REGULARIZATION_PARAMETER])
        self.solve(regparam)
       
    
    
    def solve(self, regparam):
        self.regparam = regparam
        
        #Cached results
        self.evals = np.multiply(self.svals, self.svals)
        self.newevals = 1. / (self.evals + self.regparam)
        newevalslamtilde = np.multiply(self.evals, self.newevals)
        self.D = np.sqrt(newevalslamtilde)
        #self.D = -newevalslamtilde
        
        self.VTY = self.svecs.T * self.Y
        DVTY = np.multiply(self.D.T, self.svecs.T * self.Y)
        
        self.sqrtR = np.multiply(np.sqrt(newevalslamtilde), self.svecs)
        
        #self.R = self.svecs * multiply(newevalslamtilde.T, self.svecs.T)
        
        '''
        #Global variation
        self.R = self.sqrtR * self.sqrtR.T
        self.minus_diagRx2 = - 2 * np.diag(self.R)
        '''
        #Space efficient variation
        self.R = None
        self.minus_diagRx2 = - 2 * np.array(np.sum(np.multiply(self.sqrtR, self.sqrtR), axis = 1)).reshape((self.size))
        #'''
        
        self.RY = self.sqrtR * (self.sqrtR.T * self.Y)
        self.Y_Schur_RY = np.multiply(self.Y, self.RY)
        
        #Using lists in order to avoid unnecessary matrix slicings
        #self.DVTY_list = []
        #self.YTVDDVTY_list = []
        self.YTRY_list = []
        self.classFitnessList = []
        for i in range(self.labelcount):
            #DVTY_i = DVTY[:,i]
            #self.DVTY_list.append(DVTY_i)
            YTRY_i = self.Y[:,i].T * self.RY[:,i]
            self.YTRY_list.append(YTRY_i)
            fitness_i = self.size - YTRY_i
            self.classFitnessList.append(fitness_i[0, 0])
        self.classFitnessRowVec = np.array(self.classFitnessList)
        
        converged = False
        #print self.classcounts.T
        self.callback()
        '''while True:
            
            converged = self.findSteepestDir()
            print self.classcounts.T
            self.callback()
            if converged: break
        
        '''
        
        '''
        cons = self.size / self.labelcount
        #self.focusset = self.findNewFocusSet()
        for i in range(20):
            #self.focusset = self.findNewFocusSet()
            #self.focusset = pyrandom.sample(range(self.size),50)
            #print self.focusset
            #cons = len(self.focusset) / self.labelcount
            #converged = self.findSteepestDirRotateClasses(cons / (2. ** i))
            converged = self.findSteepestDirRotateClasses(cons / (2. ** i))
            #converged = self.findSteepestDirRotateClasses(1000)
            #print self.classcounts.T
            self.callback()
            if converged: break
        
        if self.oneclass:
            self.Y = self.Y[:, 0]
        self.resource_pool[data_sources.PREDICTED_CLUSTERS_FOR_TRAINING_DATA] = self.Y
        '''
    
    
    def computeGlobalFitness(self):
        fitness = 0.
        for classind in range(self.labelcount):
            fitness += self.classFitnessList[classind]
        return fitness
    
    
    def updateA(self):
        self.A = self.svecs * multiply(self.newevals.T, self.VTY)
    
    
    def new_working_set(self, working_set):
        self.working_set = working_set
        self.RY = self.sqrtR * (self.sqrtR.T * self.Y)
        self.Y_Schur_RY = np.multiply(self.Y, self.RY)
        
        self.Y_ws = self.Y[working_set]
        #self.R_ws = self.R[np.ix_(working_set, working_set)]
        self.R_ws = self.sqrtR[working_set] * self.sqrtR[working_set].T
        self.RY_ws = self.RY[working_set]
        self.Y_Schur_RY_ws = self.Y_Schur_RY[working_set]
        self.minus_diagRx2_ws = self.minus_diagRx2[working_set]
        self.classvec_ws = self.classvec[working_set]
        self.size_ws = len(working_set)
        
        self.classcounts_ws = np.zeros((self.labelcount), dtype = np.int32)
        for i in range(self.labelcount):
            self.classcounts_ws[i] = self.size_ws - np.count_nonzero(self.classvec_ws - i)
    
    
    def claim_all_points_in_working_set(self, newclazz):
        working_set = self.working_set
        try:
            for i in range(len(working_set)):
                self.claim_a_point(newclazz)
        except Exception as e:
            print e
        '''
        steepestdir, oldclazz = cython_mmc.claim_all_points_in_working_set(self.Y_ws,
                                 self.R_ws,
                                 self.RY_ws,
                                 self.Y_Schur_RY_ws,
                                 self.minus_diagRx2_ws,
                                 self.classcounts_ws,
                                 self.classvec_ws,
                                 self.size_ws,
                                 self.sqrtR,
                                 self.sqrtR.shape[1],
                                 newclazz)
        '''
    
    
    def claim_a_point(self, newclazz):
        working_set = self.working_set
        if self.classcounts_ws[newclazz] == self.size_ws:
            raise Exception('The whole working set already belongs to class '+str(newclazz))
            #return
#         Y = self.Y[working_set]
#         #print working_set
#         R = self.R[ix_(working_set, working_set)]
#         RY = self.RY[working_set]
#         Y_Schur_RY = self.Y_Schur_RY[working_set]
#         minus_diagRx2 = self.minus_diagRx2[working_set]
#         classvec = self.classvec[working_set]
#         size = len(working_set)
        #print self.classcounts_ws, self.classvec_ws
        use_full_caches = 0
        steepestdir, oldclazz = cython_mmc.claim_a_point(self.Y_ws,
                                 self.R_ws,
                                 self.RY_ws,
                                 self.Y_Schur_RY_ws,
                                 self.minus_diagRx2_ws,
                                 self.classcounts_ws,
                                 self.classvec_ws,
                                 self.size_ws,
                                 use_full_caches,
                                 self.sqrtR,
                                 self.sqrtR.shape[1],
                                 newclazz)
        #Update global books
        self.Y[working_set] = self.Y_ws
        self.RY[working_set] = self.RY_ws
        self.Y_Schur_RY[working_set] = self.Y_Schur_RY_ws
        self.classvec[working_set] = self.classvec_ws
        self.classcounts[oldclazz] -= 1
        self.classcounts[newclazz] += 1
        
        global_steepestdir = working_set[steepestdir]
        return global_steepestdir
    
    
    def findSteepestDirRotateClasses(self, howmany, LOO = False):
        
        working_set = pyrandom.sample(range(self.size), self.size)
        Y = self.Y[working_set]
        R = self.R[ix_(working_set, working_set)]
        RY = self.RY[working_set]
        Y_Schur_RY = self.Y_Schur_RY[working_set]
        minus_diagRx2 = self.minus_diagRx2[working_set]
        classvec = self.classvec[working_set]
        size = len(working_set)
        
        cython_mmc.findSteepestDirRotateClasses(Y,
                                                R,
                                                RY,
                                                Y_Schur_RY,
                                                self.classFitnessRowVec,
                                                minus_diagRx2,
                                                self.classcounts,
                                                classvec,
                                                size,
                                                self.labelcount,
                                                howmany,
                                                self.sqrtR,
                                                self.sqrtR.shape[1])
        self.Y[working_set] = Y
        self.RY[working_set] = RY
        self.Y_Schur_RY[working_set] = Y_Schur_RY
        self.classvec[working_set] = classvec
        return
    
    
    def findSteepestDirRotateClasses_(self, howmany, LOO = False):
        cython_mmc.findSteepestDirRotateClasses(self.Y,
                                                self.R,
                                                self.RY,
                                                self.Y_Schur_RY,
                                                self.classFitnessRowVec,
                                                self.minus_diagRx2,
                                                self.classcounts,
                                                self.classvec,
                                                self.size,
                                                self.labelcount,
                                                howmany,
                                                self.sqrtR,
                                                self.sqrtR.shape[1])
        return
        
        #The slow python code. Use the above cython instead.
        for newclazz in range(self.labelcount):
            
            #!!!!!!!!!!!!!!!
            takenum = (self.size / self.labelcount) - self.classcounts[newclazz] + int(howmany)
            
            for h in range(takenum):
                dirsneg = self.classFitnessRowVec + (2 * self.minus_diagRx2[:, None] + 4 * multiply(self.Y, self.RY))
                dirsnegdiff = dirsneg - self.classFitnessRowVec
                dirscc = dirsnegdiff[arange(self.size), self.classvec].T
                dirs = dirsnegdiff + dirscc
                dirs[arange(self.size), self.classvec] = float('Inf')
                dirs = dirs[:, newclazz]
                steepestdir = argmin(dirs)
                steepness = amin(dirs)
                oldclazz = self.classvec[steepestdir]
                self.Y[steepestdir, oldclazz] = -1.
                self.Y[steepestdir, newclazz] = 1.
                self.classvec[steepestdir] = newclazz
                self.classcounts[oldclazz] = self.classcounts[oldclazz] - 1
                self.classcounts[newclazz] = self.classcounts[newclazz] + 1
                self.RY[:, oldclazz] = self.RY[:, oldclazz] - 2 * self.R[:, steepestdir]
                self.RY[:, newclazz] = self.RY[:, newclazz] + 2 * self.R[:, steepestdir]
                
                for i in range(self.labelcount):
                    YTRY_i = self.Y[:,i].T * self.RY[:,i]
                    fitness_i = self.size - YTRY_i
                    self.classFitnessRowVec[i] = fitness_i[0, 0]
                
                self.updateA()
            #self.callback()
        return False
        





class RandomLabelSource(object):
    
    def __init__(self, size, labelcount):
        self.rand = Random()
        self.rand.seed(100)
        self.Y = - np.ones((size, labelcount), dtype = np.float64)
        self.classvec = - np.ones((size, 1), dtype = np.int32)
        allinds = set(range(size))
        self.classcounts = np.zeros((labelcount, 1), dtype = np.int32)
        for i in range(labelcount-1):
            inds = self.rand.sample(allinds, size / labelcount) #sampling without replacement
            allinds = allinds - set(inds)
            for ind in inds:
                self.Y[ind, i] = 1.
                self.classvec[ind, 0] = i
                self.classcounts[i, 0] += 1
        for ind in allinds:
            self.Y[ind, labelcount - 1] = 1.
            self.classvec[ind, 0] = labelcount - 1
            self.classcounts[labelcount - 1, 0] += 1
    
    def readLabels(self):
        return self.Y

