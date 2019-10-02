# Copyright (c) 2016-2018, The University of Texas at Austin 
# & University of California--Merced.
# Copyright (c) 2019, The University of Texas at Austin 
# University of California--Merced, Washington University in St. Louis.
#
# All Rights reserved.
# See file COPYRIGHT for details.
#
# This file is part of the hIPPYlib library. For more information and source code
# availability see https://hippylib.github.io.
#
# hIPPYlib is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License (as published by the Free
# Software Foundation) version 2.0 dated June 1991.

import dolfin as dl
import numpy as np
import matplotlib.pyplot as plt

import sys
import os
sys.path.append( os.environ.get('HIPPYLIB_BASE_DIR', "../../") )
from hippylib import *


def u_boundary(x, on_boundary):
    return on_boundary

class Poisson:
    def __init__(self, mesh, Vh, Prior):
        """
        Construct a model by proving
        - the mesh
        - the finite element spaces for the STATE/ADJOINT variable and the PARAMETER variable
        - the Prior information
        """
        self.mesh = mesh
        self.Vh = Vh
        
        # Initialize Expressions
        self.mtrue = dl.Expression('std::log(2 + 7*(std::pow(std::pow(x[0] - 0.5,2) + std::pow(x[1] - 0.5,2),0.5) > 0.2))',
                                element=Vh[PARAMETER].ufl_element())
        self.f = dl.Constant(1.0)
        self.u_o = dl.Vector()
        
        self.u_bdr = dl.Constant(0.0)
        self.u_bdr0 = dl.Constant(0.0)
        self.bc = dl.DirichletBC(self.Vh[STATE], self.u_bdr, u_boundary)
        self.bc0 = dl.DirichletBC(self.Vh[STATE], self.u_bdr0, u_boundary)
        
        # Assemble constant matrices      
        self.prior = Prior
        self.Wuu = self.assembleWuu()
        

        self.computeObservation(self.u_o)
                
        self.A = None
        self.At = None
        self.C = None
        self.Wmm = None
        self.Wmu = None
        
        self.gauss_newton_approx=False
        
    def generate_vector(self, component="ALL"):
        """
        Return the list x=[u,m,p] where:
        - u is any object that describes the state variable
        - m is a Vector object that describes the parameter variable.
          (Need to support linear algebra operations)
        - p is any object that describes the adjoint variable
        
        If component is STATE, PARAMETER, or ADJOINT return x[component]
        """
        if component == "ALL":
            x = [dl.Vector(), dl.Vector(), dl.Vector()]
            self.Wuu.init_vector(x[STATE],0)
            self.prior.init_vector(x[PARAMETER],0)
            self.Wuu.init_vector(x[ADJOINT], 0)
        elif component == STATE:
            x = dl.Vector()
            self.Wuu.init_vector(x,0)
        elif component == PARAMETER:
            x = dl.Vector()
            self.prior.init_vector(x,0)
        elif component == ADJOINT:
            x = dl.Vector()
            self.Wuu.init_vector(x,0)
            
        return x
    
    def init_parameter(self, m):
        """
        Reshape m so that it is compatible with the parameter variable
        """
        self.prior.init_vector(m,0)
        
    def assembleA(self,x, assemble_adjoint = False, assemble_rhs = False):
        """
        Assemble the matrices and rhs for the forward/adjoint problems
        """
        trial = dl.TrialFunction(self.Vh[STATE])
        test = dl.TestFunction(self.Vh[STATE])
        m = vector2Function(x[PARAMETER], self.Vh[PARAMETER])
        Avarf = dl.inner(dl.exp(m)*dl.grad(trial), dl.grad(test))*dl.dx
        if not assemble_adjoint:
            bform = dl.inner(self.f, test)*dl.dx
            Matrix, rhs = dl.assemble_system(Avarf, bform, self.bc)
        else:
            # Assemble the adjoint of A (i.e. the transpose of A)
            u = vector2Function(x[STATE], self.Vh[STATE])
            obs = vector2Function(self.u_o, self.Vh[STATE])
            bform = dl.inner(obs - u, test)*dl.dx
            Matrix, rhs = dl.assemble_system(dl.adjoint(Avarf), bform, self.bc0)
            
        if assemble_rhs:
            return Matrix, rhs
        else:
            return Matrix
    
    def assembleC(self, x):
        """
        Assemble the derivative of the forward problem with respect to the parameter
        """
        trial = dl.TrialFunction(self.Vh[PARAMETER])
        test = dl.TestFunction(self.Vh[STATE])
        u = vector2Function(x[STATE], Vh[STATE])
        m = vector2Function(x[PARAMETER], Vh[PARAMETER])
        Cvarf = dl.inner(dl.exp(m) * trial * dl.grad(u), dl.grad(test)) * dl.dx
        C = dl.assemble(Cvarf)
#        print ( "||m||", x[PARAMETER].norm("l2"), "||u||", x[STATE].norm("l2"), "||C||", C.norm("linf") )
        self.bc0.zero(C)
        return C
       
    def assembleWuu(self):
        """
        Assemble the misfit operator
        """
        trial = dl.TrialFunction(self.Vh[STATE])
        test = dl.TestFunction(self.Vh[STATE])
        varf = dl.inner(trial, test)*dl.dx
        Wuu = dl.assemble(varf)
        Wuu_t = Transpose(Wuu)
        self.bc0.zero(Wuu_t)
        Wuu = Transpose(Wuu_t)
        self.bc0.zero(Wuu)
        return Wuu
    
    def assembleWmu(self, x):
        """
        Assemble the derivative of the parameter equation with respect to the state
        """
        trial = dl.TrialFunction(self.Vh[STATE])
        test  = dl.TestFunction(self.Vh[PARAMETER])
        p = vector2Function(x[ADJOINT], self.Vh[ADJOINT])
        m = vector2Function(x[PARAMETER], self.Vh[PARAMETER])
        varf = dl.inner(dl.exp(m)*dl.grad(trial),dl.grad(p))*test*dl.dx
        Wmu = dl.assemble(varf)
        Wmu_t = Transpose(Wmu)
        self.bc0.zero(Wmu_t)
        Wmu = Transpose(Wmu_t)
        return Wmu
    
    def assembleWmm(self, x):
        """
        Assemble the derivative of the parameter equation with respect to the parameter (Newton method)
        """
        trial = dl.TrialFunction(self.Vh[PARAMETER])
        test  = dl.TestFunction(self.Vh[PARAMETER])
        u = vector2Function(x[STATE], self.Vh[STATE])
        m = vector2Function(x[PARAMETER], self.Vh[PARAMETER])
        p = vector2Function(x[ADJOINT], self.Vh[ADJOINT])
        varf = dl.inner(dl.grad(p),dl.exp(m)*dl.grad(u))*trial*test*dl.dx
        return dl.assemble(varf)

        
    def computeObservation(self, u_o):
        """
        Compute the synthetic observation
        """
        mt = dl.interpolate(self.mtrue, Vh[PARAMETER])
        x = [self.generate_vector(STATE), mt.vector(), None]
        A, b = self.assembleA(x, assemble_rhs = True)
        
        A.init_vector(u_o, 1)
        dl.solve(A, u_o, b, "cg", amg_method())
        
        # Create noisy data, ud
        MAX = u_o.norm("linf")
        parRandom.normal_perturb(.01 * MAX, u_o)
    
    def cost(self, x):
        """
        Given the list x = [u,m,p] which describes the state, parameter, and
        adjoint variable compute the cost functional as the sum of 
        the misfit functional and the regularization functional.
        
        Return the list [cost functional, regularization functional, misfit functional]
        
        Note: p is not needed to compute the cost functional
        """        
        assert x[STATE] is not None
                
        diff = x[STATE] - self.u_o
        Wuudiff = self.Wuu*diff
        misfit = .5 * diff.inner(Wuudiff)
        
        Rm = dl.Vector()
        self.prior.init_vector(Rm,0)
        self.prior.R.mult(x[PARAMETER], Rm)
        reg = .5 * x[PARAMETER].inner(Rm)
        
        cost = misfit + reg
        
        return cost, reg, misfit
    
    def solveFwd(self, out, x, tol=1e-9):
        """
        Solve the forward problem.
        """
        A, b = self.assembleA(x, assemble_rhs = True)
        A.init_vector(out, 1)

        solver = dl.PETScKrylovSolver(self.mesh.mpi_comm(), "cg", amg_method())

                        
        solver.parameters["relative_tolerance"] = tol
        solver.set_operator(A)
        solver.solve(out,b)
        
#        print ("FWD", (self.A*out - b).norm("l2")/b.norm("l2"), nit)

    
    def solveAdj(self, out, x, tol=1e-9):
        """
        Solve the adjoint problem.
        """
        At, badj = self.assembleA(x, assemble_adjoint = True,assemble_rhs = True)
        At.init_vector(out, 1)
                    
        solver = dl.PETScKrylovSolver(self.mesh.mpi_comm(), "cg", amg_method())

        solver.parameters["relative_tolerance"] = tol
        solver.set_operator(At)
        solver.solve(out,badj)
        
#        print ("ADJ", (self.At*out - badj).norm("l2")/badj.norm("l2"), nit)
    
    def evalGradientParameter(self,x, mg, misfit_only=False):
        """
        Evaluate the gradient for the variation parameter equation at the point x=[u,m,p].
        Parameters:
        - x = [u,m,p] the point at which to evaluate the gradient.
        - mg the variational gradient (g, mtest) being mtest a test function in the parameter space
          (Output parameter)
        
        Returns the norm of the gradient in the correct inner product g_norm = sqrt(g,g)
        """ 
        C = self.assembleC(x)

        self.prior.init_vector(mg,0)
        C.transpmult(x[ADJOINT], mg)
        if misfit_only == False:
            Rm = dl.Vector()
            self.prior.init_vector(Rm,0)
            self.prior.R.mult(x[PARAMETER], Rm)   
            mg.axpy(1., Rm)
        
        g = dl.Vector()
        self.prior.init_vector(g,1)
        
        self.prior.Msolver.solve(g, mg)
        g_norm = np.sqrt( g.inner(mg) )
        
        return g_norm
        
    
    def setPointForHessianEvaluations(self, x, gauss_newton_approx=False):  
        """
        Specify the point x = [u,m,p] at which the Hessian operator (or the Gauss-Newton approximation)
        need to be evaluated.
        """  
        self.gauss_newton_approx = gauss_newton_approx    
        self.A  = self.assembleA(x)
        self.At = self.assembleA(x, assemble_adjoint=True )
        self.C  = self.assembleC(x)
        if gauss_newton_approx:
            self.Wmu = None
            self.Wmm = None
        else:
            self.Wmu = self.assembleWmu(x)
            self.Wmm = self.assembleWmm(x)

        
    def solveFwdIncremental(self, sol, rhs, tol):
        """
        Solve the incremental forward problem for a given rhs
        """    
        solver = dl.PETScKrylovSolver(self.mesh.mpi_comm(), "cg", amg_method())

        solver.set_operator(self.A)
        solver.parameters["relative_tolerance"] = tol
        self.A.init_vector(sol,1)
        solver.solve(sol,rhs)
#        print ("FwdInc", (self.A*sol-rhs).norm("l2")/rhs.norm("l2"), nit)
        
    def solveAdjIncremental(self, sol, rhs, tol):
        """
        Solve the incremental adjoint problem for a given rhs
        """            
        
        solver = dl.PETScKrylovSolver(self.mesh.mpi_comm(), "cg", amg_method())

        solver.set_operator(self.At)
        solver.parameters["relative_tolerance"] = tol
        self.At.init_vector(sol,1)
        solver.solve(sol, rhs)
#        print ("AdjInc", (self.At*sol-rhs).norm("l2")/rhs.norm("l2"), nit)
    
    def applyC(self, dm, out):
        self.C.mult(dm,out)
    
    def applyCt(self, dp, out):
        self.C.transpmult(dp,out)
    
    def applyWuu(self, du, out, gn_approx=False):
        self.Wuu.mult(du, out)
    
    def applyWum(self, dm, out):
        if self.gauss_newton_approx:
            out.zero()
        else:
            self.Wmu.transpmult(dm,out)

    
    def applyWmu(self, du, out):
        if self.gauss_newton_approx:
            out.zero()
        else:
            self.Wmu.mult(du, out)
    
    def applyR(self, dm, out):
        self.prior.R.mult(dm, out)
        
    def Rsolver(self):        
        return self.prior.Rsolver
    
    def applyWmm(self, dm, out):
        if self.gauss_newton_approx:
            out.zero()
        else:
            self.Wmm.mult(dm, out)
            
if __name__ == "__main__":
    try:
        dl.set_log_active(False)
    except:
        pass
    nx = 64
    ny = 64
    mesh = dl.UnitSquareMesh(nx, ny)
    
    rank = dl.MPI.rank(mesh.mpi_comm())
    nproc = dl.MPI.size(mesh.mpi_comm())
        
    Vh2 = dl.FunctionSpace(mesh, 'Lagrange', 2)
    Vh1 = dl.FunctionSpace(mesh, 'Lagrange', 1)
    Vh = [Vh2, Vh1, Vh2]
    
    Prior = LaplacianPrior(Vh[PARAMETER], gamma=1e-8, delta=1e-9)
    model = Poisson(mesh, Vh, Prior)
        
    m0 = dl.interpolate(dl.Expression("sin(x[0])", element=Vh[PARAMETER].ufl_element()), Vh[PARAMETER])
    modelVerify(model, m0.vector(), 1e-12, is_quadratic = False, verbose = (rank==0))

    m0 = dl.interpolate(dl.Constant(0.0),Vh[PARAMETER])
    parameters = ReducedSpaceNewtonCG_ParameterList()
    parameters["rel_tolerance"] = 1e-9
    parameters["abs_tolerance"] = 1e-12
    parameters["max_iter"]      = 25
    parameters["inner_rel_tolerance"] = 1e-15
    parameters["globalization"] = "LS"
    parameters["GN_iter"] = 6
    if rank != 0:
        parameters["print_level"] = -1
        
    solver = ReducedSpaceNewtonCG(model, parameters)

    
    x = solver.solve([None, m0.vector(), None])
    
    if rank == 0:
        if solver.converged:
            print ("\nConverged in ", solver.it, " iterations.")
        else:
            print ("\nNot Converged")

        print ("Termination reason: ", solver.termination_reasons[solver.reason])
        print ("Final gradient norm: ", solver.final_grad_norm)
        print ("Final cost: ", solver.final_cost)
    
    model.setPointForHessianEvaluations(x, gauss_newton_approx=False)
    Hmisfit = ReducedHessian(model, solver.parameters["inner_rel_tolerance"], misfit_only=True)
    p = 20
    k = 50
    Omega = MultiVector(x[PARAMETER], k+p)
    parRandom.normal(1., Omega)

    d, U = doublePassG(Hmisfit, Prior.R, Prior.Rsolver, Omega, k, s=1, check=False)

    if rank == 0:
        plt.figure()
        plt.plot(range(0,k), d, 'b*',range(0,k), np.ones(k), '-r')
        plt.yscale('log')
        plt.show()
    
    if nproc == 1:
        xx = [vector2Function(x[i], Vh[i]) for i in range(len(Vh))]
        dl.plot(xx[STATE], title = "State")
        dl.plot(dl.exp(xx[PARAMETER]), title = "exp(Parameter)")
        dl.plot(xx[ADJOINT], title = "Adjoint")
        dl.plot(vector2Function(model.u_o, Vh[STATE]), title = "Observation")
        dl.interactive()
    
