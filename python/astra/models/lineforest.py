from peewee import (
    AutoField,
    FloatField,
    TextField,
    ForeignKeyField,
)

from playhouse.postgres_ext import ArrayField

from astra import __version__
from astra.models.base import BaseModel
from astra.models.source import Source
from astra.models.spectrum import Spectrum
from astra.models.pipeline import PipelineOutputMixin


class LineForest(BaseModel, PipelineOutputMixin):

    """A result from the LineForest pipeline."""
    
    sdss_id = ForeignKeyField(Source, index=True)
    spectrum_id = ForeignKeyField(Spectrum, index=True, lazy_load=False)
    
    #> Astra Metadata
    task_id = AutoField()
    v_astra = TextField(default=__version__)
    t_elapsed = FloatField(null=True)
    tag = TextField(default="", index=True)
    
    #> H-alpha (6562.8 +/- 200A)
    eqw_h_alpha = FloatField(null=True)
    abs_h_alpha = FloatField(null=True)
    detection_lower_h_alpha = FloatField(null=True)
    detection_upper_h_alpha = FloatField(null=True)
    eqw_percentiles_h_alpha = ArrayField(FloatField, null=True)
    abs_percentiles_h_alpha = ArrayField(FloatField, null=True)

    #> H-beta (4861.3 +/- 200 A)
    eqw_h_beta = FloatField(null=True)
    abs_h_beta = FloatField(null=True)
    detection_lower_h_beta = FloatField(null=True)
    detection_upper_h_beta = FloatField(null=True)
    eqw_percentiles_h_beta = ArrayField(FloatField, null=True)
    abs_percentiles_h_beta = ArrayField(FloatField, null=True)

    #> H-gamma (4340.5 +/- 200 A)
    eqw_h_gamma = FloatField(null=True)
    abs_h_gamma = FloatField(null=True)
    detection_lower_h_gamma = FloatField(null=True)
    detection_upper_h_gamma = FloatField(null=True)
    eqw_percentiles_h_gamma = ArrayField(FloatField, null=True)
    abs_percentiles_h_gamma = ArrayField(FloatField, null=True)

    #> H-delta (4101.7 +/- 200 A)
    eqw_h_delta = FloatField(null=True)
    abs_h_delta = FloatField(null=True)
    detection_lower_h_delta = FloatField(null=True)
    detection_upper_h_delta = FloatField(null=True)
    eqw_percentiles_h_delta = ArrayField(FloatField, null=True)
    abs_percentiles_h_delta = ArrayField(FloatField, null=True)

    #> H-epsilon (3970.1 +/- 200 A)
    eqw_h_epsilon = FloatField(null=True)
    abs_h_epsilon = FloatField(null=True)
    detection_lower_h_epsilon = FloatField(null=True)
    detection_upper_h_epsilon = FloatField(null=True)
    eqw_percentiles_h_epsilon = ArrayField(FloatField, null=True)
    abs_percentiles_h_epsilon = ArrayField(FloatField, null=True)

    #> H-8 (3889.064 +/- 200 A)
    eqw_h_8 = FloatField(null=True)
    abs_h_8 = FloatField(null=True)
    detection_lower_h_8 = FloatField(null=True)
    detection_upper_h_8 = FloatField(null=True)
    eqw_percentiles_h_8 = ArrayField(FloatField, null=True)
    abs_percentiles_h_8 = ArrayField(FloatField, null=True)

    #> H-9 (3835.391 +/- 200 A)
    eqw_h_9 = FloatField(null=True)
    abs_h_9 = FloatField(null=True)
    detection_lower_h_9 = FloatField(null=True)
    detection_upper_h_9 = FloatField(null=True)
    eqw_percentiles_h_9 = ArrayField(FloatField, null=True)
    abs_percentiles_h_9 = ArrayField(FloatField, null=True)

    #> H-10 (3797.904 +/- 200 A)
    eqw_h_10 = FloatField(null=True)
    abs_h_10 = FloatField(null=True)
    detection_lower_h_10 = FloatField(null=True)
    detection_upper_h_10 = FloatField(null=True)
    eqw_percentiles_h_10 = ArrayField(FloatField, null=True)
    abs_percentiles_h_10 = ArrayField(FloatField, null=True)
    
    #> H-11 (3770.637 +/- 200 A)
    eqw_h_11 = FloatField(null=True)
    abs_h_11 = FloatField(null=True)
    detection_lower_h_11 = FloatField(null=True)
    detection_upper_h_11 = FloatField(null=True)
    eqw_percentiles_h_11 = ArrayField(FloatField, null=True)
    abs_percentiles_h_11 = ArrayField(FloatField, null=True)

    #> H-12 (3750.158 +/- 50 A)
    eqw_h_12 = FloatField(null=True)
    abs_h_12 = FloatField(null=True)
    detection_lower_h_12 = FloatField(null=True)
    detection_upper_h_12 = FloatField(null=True)
    eqw_percentiles_h_12 = ArrayField(FloatField, null=True)
    abs_percentiles_h_12 = ArrayField(FloatField, null=True)

    #> H-13 (3734.369 +/- 50 A)
    eqw_h_13 = FloatField(null=True)
    abs_h_13 = FloatField(null=True)
    detection_lower_h_13 = FloatField(null=True)
    detection_upper_h_13 = FloatField(null=True)
    eqw_percentiles_h_13 = ArrayField(FloatField, null=True)
    abs_percentiles_h_13 = ArrayField(FloatField, null=True)

    #> H-14 (3721.945 +/- 50 A)
    eqw_h_14 = FloatField(null=True)
    abs_h_14 = FloatField(null=True)
    detection_lower_h_14 = FloatField(null=True)
    detection_upper_h_14 = FloatField(null=True)
    eqw_percentiles_h_14 = ArrayField(FloatField, null=True)
    abs_percentiles_h_14 = ArrayField(FloatField, null=True)

    #> H-15 (3711.977 +/- 50 A)
    eqw_h_15 = FloatField(null=True)
    abs_h_15 = FloatField(null=True)
    detection_lower_h_15 = FloatField(null=True)
    detection_upper_h_15 = FloatField(null=True)
    eqw_percentiles_h_15 = ArrayField(FloatField, null=True)
    abs_percentiles_h_15 = ArrayField(FloatField, null=True)
    
    #> H-16 (3703.859 +/- 50 A)
    eqw_h_16 = FloatField(null=True)
    abs_h_16 = FloatField(null=True)
    detection_lower_h_16 = FloatField(null=True)
    detection_upper_h_16 = FloatField(null=True)
    eqw_percentiles_h_16 = ArrayField(FloatField, null=True)
    abs_percentiles_h_16 = ArrayField(FloatField, null=True)

    #> H-17 (3697.157 +/- 50 A)
    eqw_h_17 = FloatField(null=True)
    abs_h_17 = FloatField(null=True)
    detection_lower_h_17 = FloatField(null=True)
    detection_upper_h_17 = FloatField(null=True)
    eqw_percentiles_h_17 = ArrayField(FloatField, null=True)
    abs_percentiles_h_17 = ArrayField(FloatField, null=True)

    #> Pa-7 (10049.4889 +/- 200 A)
    eqw_pa_7 = FloatField(null=True)
    abs_pa_7 = FloatField(null=True)
    detection_lower_pa_7 = FloatField(null=True)
    detection_upper_pa_7 = FloatField(null=True)
    eqw_percentiles_pa_7 = ArrayField(FloatField, null=True)
    abs_percentiles_pa_7 = ArrayField(FloatField, null=True)

    #> Pa-8 (9546.0808 +/- 200 A)
    eqw_pa_8 = FloatField(null=True)
    abs_pa_8 = FloatField(null=True)
    detection_lower_pa_8 = FloatField(null=True)
    detection_upper_pa_8 = FloatField(null=True)
    eqw_percentiles_pa_8 = ArrayField(FloatField, null=True)
    abs_percentiles_pa_8 = ArrayField(FloatField, null=True)

    #> Pa-9 (9229.12 +/- 200 A)
    eqw_pa_9 = FloatField(null=True)
    abs_pa_9 = FloatField(null=True)
    detection_lower_pa_9 = FloatField(null=True)
    detection_upper_pa_9 = FloatField(null=True)
    eqw_percentiles_pa_9 = ArrayField(FloatField, null=True)
    abs_percentiles_pa_9 = ArrayField(FloatField, null=True)

    #> Pa-10 (9014.909 +/- 200 A)
    eqw_pa_10 = FloatField(null=True)
    abs_pa_10 = FloatField(null=True)
    detection_lower_pa_10 = FloatField(null=True)
    detection_upper_pa_10 = FloatField(null=True)
    eqw_percentiles_pa_10 = ArrayField(FloatField, null=True)
    abs_percentiles_pa_10 = ArrayField(FloatField, null=True)

    #> Pa-11 (8862.782 +/- 200 A)
    eqw_pa_11 = FloatField(null=True)
    abs_pa_11 = FloatField(null=True)
    detection_lower_pa_11 = FloatField(null=True)
    detection_upper_pa_11 = FloatField(null=True)
    eqw_percentiles_pa_11 = ArrayField(FloatField, null=True)
    abs_percentiles_pa_11 = ArrayField(FloatField, null=True)

    #> Pa-12 (8750.472 +/- 200 A)
    eqw_pa_12 = FloatField(null=True)
    abs_pa_12 = FloatField(null=True)
    detection_lower_pa_12 = FloatField(null=True)
    detection_upper_pa_12 = FloatField(null=True)
    eqw_percentiles_pa_12 = ArrayField(FloatField, null=True)
    abs_percentiles_pa_12 = ArrayField(FloatField, null=True)

    #> Pa-13 (8665.019 +/- 200 A)
    eqw_pa_13 = FloatField(null=True)
    abs_pa_13 = FloatField(null=True)
    detection_lower_pa_13 = FloatField(null=True)
    detection_upper_pa_13 = FloatField(null=True)
    eqw_percentiles_pa_13 = ArrayField(FloatField, null=True)
    abs_percentiles_pa_13 = ArrayField(FloatField, null=True)

    #> Pa-14 (8598.392 +/- 200 A)
    eqw_pa_14 = FloatField(null=True)
    abs_pa_14 = FloatField(null=True)
    detection_lower_pa_14 = FloatField(null=True)
    detection_upper_pa_14 = FloatField(null=True)
    eqw_percentiles_pa_14 = ArrayField(FloatField, null=True)
    abs_percentiles_pa_14 = ArrayField(FloatField, null=True)

    #> Pa-15 (8545.383 +/- 200 A)
    eqw_pa_15 = FloatField(null=True)
    abs_pa_15 = FloatField(null=True)
    detection_lower_pa_15 = FloatField(null=True)
    detection_upper_pa_15 = FloatField(null=True)
    eqw_percentiles_pa_15 = ArrayField(FloatField, null=True)
    abs_percentiles_pa_15 = ArrayField(FloatField, null=True)

    #> Pa-16 (8502.483 +/- 200 A)
    eqw_pa_16 = FloatField(null=True)
    abs_pa_16 = FloatField(null=True)
    detection_lower_pa_16 = FloatField(null=True)
    detection_upper_pa_16 = FloatField(null=True)
    eqw_percentiles_pa_16 = ArrayField(FloatField, null=True)
    abs_percentiles_pa_16 = ArrayField(FloatField, null=True)

    #> Pa-17 (8467.254 +/- 200 A)
    eqw_pa_17 = FloatField(null=True)
    abs_pa_17 = FloatField(null=True)
    detection_lower_pa_17 = FloatField(null=True)
    detection_upper_pa_17 = FloatField(null=True)
    eqw_percentiles_pa_17 = ArrayField(FloatField, null=True)
    abs_percentiles_pa_17 = ArrayField(FloatField, null=True)

    #> Ca II (8662.14 +/- 50 A)
    eqw_ca_ii_8662 = FloatField(null=True)
    abs_ca_ii_8662 = FloatField(null=True)
    detection_lower_ca_ii_8662 = FloatField(null=True)
    detection_upper_ca_ii_8662 = FloatField(null=True)
    eqw_percentiles_ca_ii_8662 = ArrayField(FloatField, null=True)
    abs_percentiles_ca_ii_8662 = ArrayField(FloatField, null=True)

    #> Ca II (8542.089 +/- 50 A)
    eqw_ca_ii_8542 = FloatField(null=True)
    abs_ca_ii_8542 = FloatField(null=True)
    detection_lower_ca_ii_8542 = FloatField(null=True)
    detection_upper_ca_ii_8542 = FloatField(null=True)
    eqw_percentiles_ca_ii_8542 = ArrayField(FloatField, null=True)
    abs_percentiles_ca_ii_8542 = ArrayField(FloatField, null=True)

    #> Ca II (8498.018 +/- 50 A)
    eqw_ca_ii_8498 = FloatField(null=True)
    abs_ca_ii_8498 = FloatField(null=True)
    detection_lower_ca_ii_8498 = FloatField(null=True)
    detection_upper_ca_ii_8498 = FloatField(null=True)
    eqw_percentiles_ca_ii_8498 = ArrayField(FloatField, null=True)
    abs_percentiles_ca_ii_8498 = ArrayField(FloatField, null=True)

    #> Ca K (3933.6614 +/- 200 A)
    eqw_ca_k_3933 = FloatField(null=True)
    abs_ca_k_3933 = FloatField(null=True)
    detection_lower_ca_k_3933 = FloatField(null=True)
    detection_upper_ca_k_3933 = FloatField(null=True)
    eqw_percentiles_ca_k_3933 = ArrayField(FloatField, null=True)
    abs_percentiles_ca_k_3933 = ArrayField(FloatField, null=True)

    #> Ca H (3968.4673 +/- 200 A)
    eqw_ca_h_3968 = FloatField(null=True)
    abs_ca_h_3968 = FloatField(null=True)
    detection_lower_ca_h_3968 = FloatField(null=True)
    detection_upper_ca_h_3968 = FloatField(null=True)
    eqw_percentiles_ca_h_3968 = ArrayField(FloatField, null=True)
    abs_percentiles_ca_h_3968 = ArrayField(FloatField, null=True)

    #> He I (6678.151 +/- 50 A)
    eqw_he_i_6678 = FloatField(null=True)
    abs_he_i_6678 = FloatField(null=True)
    detection_lower_he_i_6678 = FloatField(null=True)
    detection_upper_he_i_6678 = FloatField(null=True)
    eqw_percentiles_he_i_6678 = ArrayField(FloatField, null=True)
    abs_percentiles_he_i_6678 = ArrayField(FloatField, null=True)

    #> He I (5875.621 +/- 50 A)
    eqw_he_i_5875 = FloatField(null=True)
    abs_he_i_5875 = FloatField(null=True)
    detection_lower_he_i_5875 = FloatField(null=True)
    detection_upper_he_i_5875 = FloatField(null=True)
    eqw_percentiles_he_i_5875 = ArrayField(FloatField, null=True)
    abs_percentiles_he_i_5875 = ArrayField(FloatField, null=True)

    #> He I (5015.678 +/- 50 A)
    eqw_he_i_5015 = FloatField(null=True)
    abs_he_i_5015 = FloatField(null=True)
    detection_lower_he_i_5015 = FloatField(null=True)
    detection_upper_he_i_5015 = FloatField(null=True)
    eqw_percentiles_he_i_5015 = ArrayField(FloatField, null=True)
    abs_percentiles_he_i_5015 = ArrayField(FloatField, null=True)

    #> He I (4471.479 +/- 50 A)
    eqw_he_i_4471 = FloatField(null=True)
    abs_he_i_4471 = FloatField(null=True)
    detection_lower_he_i_4471 = FloatField(null=True)
    detection_upper_he_i_4471 = FloatField(null=True)
    eqw_percentiles_he_i_4471 = ArrayField(FloatField, null=True)
    abs_percentiles_he_i_4471 = ArrayField(FloatField, null=True)

    #> He II (4685.7 +/- 50 A)
    eqw_he_ii_4685 = FloatField(null=True)
    abs_he_ii_4685 = FloatField(null=True)
    detection_lower_he_ii_4685 = FloatField(null=True)
    detection_upper_he_ii_4685 = FloatField(null=True)
    eqw_percentiles_he_ii_4685 = ArrayField(FloatField, null=True)
    abs_percentiles_he_ii_4685 = ArrayField(FloatField, null=True)

    #> N II (6583.45 +/- 50 A)
    eqw_n_ii_6583 = FloatField(null=True)
    abs_n_ii_6583 = FloatField(null=True)
    detection_lower_n_ii_6583 = FloatField(null=True)
    detection_upper_n_ii_6583 = FloatField(null=True)
    eqw_percentiles_n_ii_6583 = ArrayField(FloatField, null=True)
    abs_percentiles_n_ii_6583 = ArrayField(FloatField, null=True)

    #> N II (6548.05 +/- 50 A)
    eqw_n_ii_6548 = FloatField(null=True)
    abs_n_ii_6548 = FloatField(null=True)
    detection_lower_n_ii_6548 = FloatField(null=True)
    detection_upper_n_ii_6548 = FloatField(null=True)
    eqw_percentiles_n_ii_6548 = ArrayField(FloatField, null=True)
    abs_percentiles_n_ii_6548 = ArrayField(FloatField, null=True)

    #> S II (6716.44 +/- 50 A)
    eqw_s_ii_6716 = FloatField(null=True)
    abs_s_ii_6716 = FloatField(null=True)
    detection_lower_s_ii_6716 = FloatField(null=True)
    detection_upper_s_ii_6716 = FloatField(null=True)
    eqw_percentiles_s_ii_6716 = ArrayField(FloatField, null=True)
    abs_percentiles_s_ii_6716 = ArrayField(FloatField, null=True)

    #> S II (6730.816 +/- 50 A)
    eqw_s_ii_6730 = FloatField(null=True)
    abs_s_ii_6730 = FloatField(null=True)
    detection_lower_s_ii_6730 = FloatField(null=True)
    detection_upper_s_ii_6730 = FloatField(null=True)
    eqw_percentiles_s_ii_6730 = ArrayField(FloatField, null=True)
    abs_percentiles_s_ii_6730 = ArrayField(FloatField, null=True)

    #> Fe II (5018.434 +/- 50 A)
    eqw_fe_ii_5018 = FloatField(null=True)
    abs_fe_ii_5018 = FloatField(null=True)
    detection_lower_fe_ii_5018 = FloatField(null=True)
    detection_upper_fe_ii_5018 = FloatField(null=True)
    eqw_percentiles_fe_ii_5018 = ArrayField(FloatField, null=True)
    abs_percentiles_fe_ii_5018 = ArrayField(FloatField, null=True)

    #> Fe II (5169.03 +/- 50 A)
    eqw_fe_ii_5169 = FloatField(null=True)
    abs_fe_ii_5169 = FloatField(null=True)
    detection_lower_fe_ii_5169 = FloatField(null=True)
    detection_upper_fe_ii_5169 = FloatField(null=True)
    eqw_percentiles_fe_ii_5169 = ArrayField(FloatField, null=True)
    abs_percentiles_fe_ii_5169 = ArrayField(FloatField, null=True)

    #> Fe II (5197.577 +/- 50 A)
    eqw_fe_ii_5197 = FloatField(null=True)
    abs_fe_ii_5197 = FloatField(null=True)
    detection_lower_fe_ii_5197 = FloatField(null=True)
    detection_upper_fe_ii_5197 = FloatField(null=True)
    eqw_percentiles_fe_ii_5197 = ArrayField(FloatField, null=True)
    abs_percentiles_fe_ii_5197 = ArrayField(FloatField, null=True)

    #> Fe II (6432.68 +/- 50 A)
    eqw_fe_ii_6432 = FloatField(null=True)
    abs_fe_ii_6432 = FloatField(null=True)
    detection_lower_fe_ii_6432 = FloatField(null=True)
    detection_upper_fe_ii_6432 = FloatField(null=True)
    eqw_percentiles_fe_ii_6432 = ArrayField(FloatField, null=True)
    abs_percentiles_fe_ii_6432 = ArrayField(FloatField, null=True)

    #> O I (5577.339 +/- 50 A)
    eqw_o_i_5577 = FloatField(null=True)
    abs_o_i_5577 = FloatField(null=True)
    detection_lower_o_i_5577 = FloatField(null=True)
    detection_upper_o_i_5577 = FloatField(null=True)
    eqw_percentiles_o_i_5577 = ArrayField(FloatField, null=True)
    abs_percentiles_o_i_5577 = ArrayField(FloatField, null=True)

    #> O I (6300.304 +/- 50 A)
    eqw_o_i_6300 = FloatField(null=True)
    abs_o_i_6300 = FloatField(null=True)
    detection_lower_o_i_6300 = FloatField(null=True)
    detection_upper_o_i_6300 = FloatField(null=True)
    eqw_percentiles_o_i_6300 = ArrayField(FloatField, null=True)
    abs_percentiles_o_i_6300 = ArrayField(FloatField, null=True)

    #> O I (6363.777 +/- 50 A)
    eqw_o_i_6363 = FloatField(null=True)
    abs_o_i_6363 = FloatField(null=True)
    detection_lower_o_i_6363 = FloatField(null=True)
    detection_upper_o_i_6363 = FloatField(null=True)
    eqw_percentiles_o_i_6363 = ArrayField(FloatField, null=True)
    abs_percentiles_o_i_6363 = ArrayField(FloatField, null=True)

    #> O II (3727.42 +/- 50 A)
    eqw_o_ii_3727 = FloatField(null=True)
    abs_o_ii_3727 = FloatField(null=True)
    detection_lower_o_ii_3727 = FloatField(null=True)
    detection_upper_o_ii_3727 = FloatField(null=True)
    eqw_percentiles_o_ii_3727 = ArrayField(FloatField, null=True)
    abs_percentiles_o_ii_3727 = ArrayField(FloatField, null=True)

    #> O III (4958.911 +/- 50 A)
    eqw_o_iii_4959 = FloatField(null=True)
    abs_o_iii_4959 = FloatField(null=True)
    detection_lower_o_iii_4959 = FloatField(null=True)
    detection_upper_o_iii_4959 = FloatField(null=True)
    eqw_percentiles_o_iii_4959 = ArrayField(FloatField, null=True)
    abs_percentiles_o_iii_4959 = ArrayField(FloatField, null=True)

    #> O III (5006.843 +/- 50 A)
    eqw_o_iii_5006 = FloatField(null=True)
    abs_o_iii_5006 = FloatField(null=True)
    detection_lower_o_iii_5006 = FloatField(null=True)
    detection_upper_o_iii_5006 = FloatField(null=True)
    eqw_percentiles_o_iii_5006 = ArrayField(FloatField, null=True)
    abs_percentiles_o_iii_5006 = ArrayField(FloatField, null=True)

    #> O III (4363.85 +/- 50 A)
    eqw_o_iii_4363 = FloatField(null=True)
    abs_o_iii_4363 = FloatField(null=True)
    detection_lower_o_iii_4363 = FloatField(null=True)
    detection_upper_o_iii_4363 = FloatField(null=True)
    eqw_percentiles_o_iii_4363 = ArrayField(FloatField, null=True)
    abs_percentiles_o_iii_4363 = ArrayField(FloatField, null=True)

    #> Li I (6707.76 +/- 50 A)
    eqw_li_i = FloatField(null=True)
    abs_li_i = FloatField(null=True)
    detection_lower_li_i = FloatField(null=True)
    detection_upper_li_i = FloatField(null=True)
    eqw_percentiles_li_i = ArrayField(FloatField, null=True)
    abs_percentiles_li_i = ArrayField(FloatField, null=True)
