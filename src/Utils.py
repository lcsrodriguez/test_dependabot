# Importing all the libraries
import numpy as np
import numpy.random as npr
import time
import warnings
import scipy
import random
import pandas as pd
import matplotlib.pyplot as plt
from enum import Enum
import missingno as msn
import QuantLib as ql
from .Constants import *
from tqdm.notebook import trange, tqdm
from typing import List, Union, Any
import multiprocessing
import os

# Setting default figure sizes for Matplotlib
plt.rcParams["figure.figsize"] = [10, 5] # Figure sizes for Matplotlib 
plt.rcParams["axes.prop_cycle"] = plt.cycler(color=["blue", "green", "red", "orange", "purple", "magenta", "gray", "black"]) # Color for plotting

# Silencing all warnings for a better UX
warnings.filterwarnings("ignore")

# Setting up a fixed random seed for experiment purposes
#npr.seed(1)


class Utils:
    r"""
    Static class for utils functions
    """

    @staticmethod
    def get_multiprocessing_infos() -> dict:
        r"""Function returning several informations about multiprocessing application

        Returns:
            dict: Hashtable of information
        """
        # Returning useful informations
        return {
            "AVAILABLE_CPU_CORES": os.cpu_count(),
            "MP_ACTIVE_CHILDREN": multiprocessing.active_children(),
            "MP_CPU_COUNT": multiprocessing.cpu_count()
        }
    
    @staticmethod
    def get_dict_values(x: dict) -> Any:
        r"""Function taking a random dictionary and unpacking it by returning its values

        Args:
            x (dict): Dictionary (Hashmap)

        Returns:
            Any: Values
        """
        return x.values()
    
    @staticmethod
    def plot_MC_convergence_evolution(data: pd.DataFrame) -> None:
        r"""Function plotting the evolution of the convergence of the Monte-Carlo option price

        Args:
            data (pd.DataFrame): Data generated by Pricer.get_MC_convergence_evolution()

        Returns:
            None: No return (only plot on stdout)
        """

        # Setting up the colors array
        colors = ["blue", "green", "orange", "purple", "magenta"]

        # Plotting the MC price
        data.T["price"].plot(color="red", label="MC price")

        # Retrieving the ci intervals to get the keys for looping
        ci = data.T["ci"].iloc[0]

        # For each level, plotting the CI intervals
        for i, ci_level in enumerate(list(ci.keys())):
            data.T["ci"].apply(pd.Series)[ci_level].apply(pd.Series)["lower"].plot(color=colors[i], label=f"Level {ci_level}%")
            data.T["ci"].apply(pd.Series)[ci_level].apply(pd.Series)["upper"].plot(color=colors[i], label="")
        
        # Plotting the mean/variance MC price over the $N_{MC}$ values
        _ = plt.axhline(y = data.T["price"].mean(), color="black", ls="-.", label="Mean MC price")
        _ = plt.axhline(y = data.T["price"].mean() - data.T["price"].var(), color="magenta", ls="-.", label="Variance MC price")
        _ = plt.axhline(y = data.T["price"].mean() + data.T["price"].var(), color="magenta", ls="-.", label="")
        
        # Plotting options
        _ = plt.xlabel("Values of $N_{MC}$")
        _ = plt.ylabel("Price")
        _ = plt.title("Evolution of the Monte-Carlo simulated price\nConvergence with respect to the number of simulations $N_{MC}$")
        _ = plt.legend()
        _ = plt.grid()

        return None

    @staticmethod
    def plot_confidence_intervals(pricer_res: dict) -> None:
        r"""Function plotting the confidence intervals and the price from a given pricer

        Args:
            pricer_res (dict): Resulting hashtable of a pricer

        Returns:
            None: No return (only plot on stdout)
        """
        # Getting pricer & confidence interval
        price, ci = Utils.get_dict_values(x=pricer_res)

        #plt.figure(figsize=(10, 5))

        # Declaring color for 
        colors = ["green", "blue", "purple", "orange", "magenta"]

        # Plotting the price line
        plt.axvline(x=price, color="red", label="MC price")

        # Removing the y-ticks
        plt.yticks([], [])

        # For each confidence interval level computed during the pricing step
        for i, ci_level in enumerate(ci.items()):
            # Getting the CI level and the upper/lower boundaries
            ci_level_ = ci_level[0]
            boundaries = ci_level[1]
            
            # Plotting for each CI, the upper and lower boundaries
            plt.axvline(x = boundaries["lower"], color=colors[i], label=f"CI {ci_level_}%", ls="-.")
            plt.axvline(x = boundaries["upper"], color=colors[i], ls="-.")
            
            # Defining the limits of the x-axis
            plt.xlim([boundaries["lower"] - 0.5, boundaries["upper"] + 0.5])
            #print(ci_level)

        # Setting the plotting options
        plt.legend(loc='center left', bbox_to_anchor=(1, 0.5), title="Markers")  
        plt.title("Confidence intervals distribution for Monte-Carlo pricing")
        plt.grid()

        return None

    @staticmethod
    def get_level_values(x: List[Constants.Level]) -> Union[List[int], List[float], List[Union[int, float]]]:
        r"""Function returning the list of the CI level values

        Args:
            x (List[Constants.Level]): List of CI levels

        Returns:
            Union[List[int], List[float], List[Union[int, float]]]: List of level values
        """
        return [level.value for level in x]

    @staticmethod
    def cast_df(x: dict | list | np.ndarray | pd.Series, *args, **kwargs) -> pd.DataFrame:
        r"""Function to explicitly cast a dictionary or Numpy array into a **pandas** `DataFrame`

        Args:
            x (dict | list | np.ndarray | pd.Series): Input data variable

        Returns:
            pd.DataFrame: Output Pandas `DataFrame`
        """
        return pd.DataFrame(x, *args, **kwargs)

    @staticmethod
    def generate_correlated_gaussians(Sigma: Union[np.ndarray, list, float], 
                                      T: float = 1.0, 
                                      N: int = Constants.MAX_STEPS, 
                                      verbose: bool = False) -> Union[np.ndarray, None]:
        r"""Function which generates a series of two Gaussian series correlated by the given
        vector of means : $\mu \in \mathbb{R}^n$ and correlation matrix $\Sigma \in \mathcal{S}_n$

        The underlying algorithm generates samples of increments from a correlated Brownian motion with a given mean $\mu$ and Variance-Covariance matrix $\Sigma$.
        
        The algorithm uses the fact that if you have $n$ independent brownian motions, the samples given by $\mu + C\times Z$ are distributed as $\mathcal{N}(\mu,\Sigma)$, where:
        
        - $Z \sim \mathcal{N}(0, 1)$ *(Gaussian variate)*
        - $\mu$ is the vector of means
        - $C$ is the square root of the Variance-Covariance matrix.

        $$C = \Sigma^{\frac{1}{2}}$$

        To compute the square root of the variance-covariance matrix $C$, the **Cholesky decomposition** is implemented.


        **Reference**: [https://quantessence.files.wordpress.com/2012/01/multibrownianmotion.pdf](https://quantessence.files.wordpress.com/2012/01/multibrownianmotion.pdf)
        
        
        Args:
            Sigma (Union[np.ndarray, list, float]): Correlation matrix or correlation ratio (float number)
            T (float, optional): Time horizon (upper bound of the time interval). Defaults to 1.0.
            N (int, optional): Number of step in the time mesh. Defaults to Constants.MAX_STEPS.
            verbose (bool, optional): Boolean to verbose. Defaults to False.

        Returns:
            Union[np.ndarray, None]: $k \in \mathbb{N}^+$ numpy arrays which corresponds to *Brownian increments* ($(dW^1_t)_t, \ldots, (dW^n_t)_t$)
        """


        # If the given correlation is a matrix (2-DIM)
        if isinstance(Sigma, float):
            rho = Sigma
            # Checking the value of rho
            assert rho < 1.0 and rho > -1.0
        
            # Creating the correlation matrix
            Sigma = np.array([[1, rho], [rho, 1]])

            # Setting the number of path to simulate to 2
            NB_PATHS = 2

        # If the given is a Numpy or "Python" matrix (N-DIM) (N > 2)
        elif isinstance(Sigma, list) or isinstance(Sigma, np.ndarray):
            if isinstance(Sigma, list):
                assert len(Sigma) == len(Sigma[0])
            if isinstance(Sigma, np.ndarray):
                assert Sigma.shape[0] == Sigma.shape[1]

            # Getting the number of correlated Gaussian sequences to be simulated
            NB_PATHS = Sigma.shape[0]

        # Performing the Cholesky decomposition
        try:
            L = np.linalg.cholesky(Sigma) # L is the lower triangular matrix, L.T is the upper triangular matrix

            # Setting up the time step
            dT = T/N
            
            # Creation of 2 Brownian motions with N steps
            X = np.random.normal(0, (dT**(1/2)), (NB_PATHS, N))
            
            # Compute the correlated paths
            CX = np.dot(L, X) # or np.dot(X, L.T)
            
            # Checking the correlation ratio of the simulated BM
            if verbose:
                corr_coeff = np.corrcoef(CX.cumsum(axis=1))[1][0]
                print("-------------- Generation of Brownian Motions --------------")
                print(f"Simulated rho: {corr_coeff} \tGiven rho: {rho}\nAbsolute error: {np.abs(corr_coeff - rho)}")
            
            # Returning the correlated Gaussian series
            return CX

        except np.linalg.LinAlgError as e:
            print("Please set a positive definite correlation matrix")
            return None
    
    def generate_correlated_brownians(*args, **kwargs) -> np.ndarray:
        r"""Function which generates a series of $k$ Brownian motions correlated by the 
        given correlation matrix 
        
        $$\Sigma \in \mathcal{S}^{++}_k$$

        Returns:
            np.ndarray: Numpy array containg the $k$ Brownian motion trajectories
        """
        sim_ = Utils.generate_correlated_gaussians(*args, **kwargs)
        if sim_ is None: return None
        return [path.cumsum() for path in sim_]