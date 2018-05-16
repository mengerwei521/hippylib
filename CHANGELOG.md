                        Inverse Problem PYthon library

```
 __        ______  _______   _______   __      __  __  __  __       
/  |      /      |/       \ /       \ /  \    /  |/  |/  |/  |      
$$ |____  $$$$$$/ $$$$$$$  |$$$$$$$  |$$  \  /$$/ $$ |$$/ $$ |____  
$$      \   $$ |  $$ |__$$ |$$ |__$$ | $$  \/$$/  $$ |/  |$$      \ 
$$$$$$$  |  $$ |  $$    $$/ $$    $$/   $$  $$/   $$ |$$ |$$$$$$$  |
$$ |  $$ |  $$ |  $$$$$$$/  $$$$$$$/     $$$$/    $$ |$$ |$$ |  $$ |
$$ |  $$ | _$$ |_ $$ |      $$ |          $$ |    $$ |$$ |$$ |__$$ |
$$ |  $$ |/ $$   |$$ |      $$ |          $$ |    $$ |$$ |$$    $$/ 
$$/   $$/ $$$$$$/ $$/       $$/           $$/     $$/ $$/ $$$$$$$/  
```                                                                    
                                                                    
                                                                    

                          https://hippylib.github.io
                          
Development Version
========================================
- **Bugfix** in `PDEVariationalProblem.solveIncremental` for non self-adjoint models 
- Add new estimator for the trace and diagonal of the prior covariance
using randomized eigendecomposition
- In all examples and tutorial, use enviromental variable `HIPPYLIB_BASE_DIR` (if defined)
to add `hIPPYlib` to `PYTHONPATH`
                          
Version 1.5.0, released on Jan 24, 2018
========================================
- Add support for FEniCS 2017.2

Version 1.4.0, released on Nov 8, 2017
========================================
- Add support for Python 3
- Enchantments in PDEVariationalProblem: it now supports multiple Dirichlet
  condition and Vector & Mixed FunctionSpaces
- Bugfix: Set the correct number of global rows, when targets points fall 
  outside the computational domain
- More extensive testing with Travis Integration                          

Version 1.3.0, released on June 28, 2017
========================================
- Improve hashdist installation support
- Switch license to GPL-2
- Add support for FEniCS 2017.1

Version 1.2.0, released on April 24, 2017
=========================================
- Update instruction to build FEniCS: hashdist and docker
- Update notebook to nbformat 4
- Let FEniCS 2016.2 be the preferred version of FEniCS
- Add travis integration
                          
Version 1.1.0, released on Nov 28, 2016
=======================================

- Add partial support for FEniCS 2016.1 (Applications and Tutorial)
- Improve performance of the randomized eigensolvers

Version 1.0.2, released on Sep 30, 2016
=======================================

- Use vector2Function to safely convert dolfin.Vector to dolfin.Function
- Optimize the PDEVariationalProblem to exploit the case when the forward problem is linear
- Update notebook 1_FEniCS101
                           
Version 1.0.1, released on Aug 25, 2016
=======================================

- Add support in hippylib.Model and hippylib.Misfit for misfit functional with explicit dependence on the parameter


Version 1.0.0, released on Aug 8, 2016
======================================

- Uploaded to https://hippylib.github.io.
- Initial release.