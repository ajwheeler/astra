import numpy as np
import os
import torch
from tqdm import tqdm
from time import time
from luigi.parameter import ParameterVisibility

import astra
from astra.contrib.apogeenet.model import Net, predict
from astra.database import astradb
from astra.tasks import BaseTask
from astra.tasks.io.sdss5 import ApStarFile
from astra.tasks.io.sdss4 import (ApStarFile as SDSS4ApStarFile)
from astra.tasks.slurm import slurm_mixin_factory, slurmify
from astra.tasks.targets import (DatabaseTarget, LocalTarget, AstraSource)
from astra.tools.spectrum import Spectrum1D
from astra.utils import log, timer

SlurmMixin = slurm_mixin_factory("APOGEENet")

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

log.debug(f"Using Torch device {device}")

class APOGEENetMixin(SlurmMixin, BaseTask):

    """ A mixin class for APOGEENet tasks. """

    task_namespace = "APOGEENet"

    model_path = astra.Parameter(
        description="The path of the trained APOGEENet model.",
        always_in_help=True,
        config_path=dict(section=task_namespace, name="model_path")
    )


class TrainedAPOGEENetModel(APOGEENetMixin):

    """ A trained APOGEENet model file. """

    def output(self):    
        return LocalTarget(self.model_path)


class EstimateStellarParameters(APOGEENetMixin):

    """
    Estimate stellar parameters of a young stellar object, given a trained APOGEENet model.

    :param model_path:
        The path of the trained APOGEENet model.

    :param uncertainty: (optional)
        The number of draws to use when calculating the uncertainty in the
        network (default: 100).
    """

    uncertainty = astra.IntParameter(
        description="The number of draws to use when calculating the uncertainty in the network.",
        default=100,
        always_in_help=True,
        visibility=ParameterVisibility.HIDDEN,
    )

    max_batch_size = 10_000

    def output(self):
        """ The output produced by this task. """
        if self.is_batch_mode:
            return (task.output() for task in self.get_batch_tasks())
        return dict(database=DatabaseTarget(astradb.ApogeeNet, self))
        

    def read_model(self):
        """ Read in the trained APOGEENet model. """

        # Load model.
        model = Net()
        model.load_state_dict(
            torch.load(
                self.get_input("model").path,
                map_location=device
            ),
            strict=False
        )
        model.to(device)
        model.eval()
        return model


    def read_observation(self):
        """ Read in the observations. """
        return Spectrum1D.read(self.get_input("observation").path)


    def estimate_stellar_parameters(self, model, spectrum):
        """
        Estimate stellar parameters given a trained APOGEENet model and a spectrum.

        :param model:
            The APOGEENet model as a torch network.
        
        :param spectrum:
            An observed spectrum.
        """

        N, P = spectrum.flux.shape
        
        # Build flux tensor as described.
        dtype = np.float32
        idx = 0

        results = { "snr": spectrum.meta["snr"] }
        for i in range(N):
                
            flux = spectrum.flux.value[i].astype(dtype)
            error = spectrum.uncertainty.array[i].astype(dtype)**-0.5

            bad = ~np.isfinite(flux) + ~np.isfinite(error)
            flux[bad] = np.nanmedian(flux)
            error[bad] = 1e+10

            flux = torch.from_numpy(flux).to(device)
            error = torch.from_numpy(error).to(device)

            flux_tensor = torch.randn(self.uncertainty, 1, P).to(device)

            median_error = torch.median(error).item()
            
            error = torch.where(error == 1.0000e+10, flux, error)
            error_t = torch.tensor(np.array([5 * median_error], dtype=dtype)).to(device)

            error = torch.where(error >= 5 * median_error, error_t, error)

            flux_tensor = flux_tensor * error + flux
            flux_tensor[0][0] = flux
        
            # Estimate quantities.
            result = predict(model, flux_tensor)
            for key, value in result.items():
                results.setdefault(key, [])
                results[key].append(value)

        return results


    @slurmify
    def run(self):
        """ Estimate stellar parameters given an APOGEENet model and ApStarFile(s). """

        model = self.read_model()

        for init, task in tqdm(timer(self.get_batch_tasks()), total=self.get_batch_size()):
            if task.complete():
                continue
        
            spectrum = task.read_observation()
            results = task.estimate_stellar_parameters(model, spectrum)

            task.output()["database"].write(results)

            # For this task, trigger the processing time event and the success event.
            task.trigger_event_processing_time(time() - init, cascade=True)

        return None


class EstimateStellarParametersGivenApStarFile(EstimateStellarParameters, ApStarFile):

    def requires(self):
        return dict(
            model=self.clone(TrainedAPOGEENetModel),
            observation=self.clone(ApStarFile)
        )
        

class EstimateStellarParametersGivenSDSS4ApStarFile(EstimateStellarParameters, SDSS4ApStarFile):

    def requires(self):
        return dict(
            model=self.clone(TrainedAPOGEENetModel),
            observation=self.clone(SDSS4ApStarFile)
        )
