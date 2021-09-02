
import os
import datetime
import numpy as np

from astra.contrib.ferre.utils import read_ferre_headers


def group_header_paths(header_paths):
    """
    Sort a list of header paths into groups based on the telescope / LSF model adopted.
    This groups data together that can be finished without waiting on other observations.
    
    :param header_paths:
        A list of FERRE header paths.
    """
    
    all_lsfs = []
    grouped_header_paths = {}
    for header_path in header_paths:
        observatory, lsf, spectral_desc = task_id_parts(header_path)
        grouped_header_paths.setdefault(observatory, {})
        grouped_header_paths[observatory].setdefault(lsf, [])
        grouped_header_paths[observatory][lsf].append((spectral_desc, header_path))
        all_lsfs.append(lsf)
    all_lsfs = list(set(all_lsfs))

    return (grouped_header_paths, all_lsfs)


def task_id_parts(header_path):
    *_, radiative_transfer_code, model_photospheres, isotopes, suffix, basename = header_path.split("/")

    parts = basename.split("_")
    _ = 4
    gd, spectral_type = (parts[1][_], parts[1][_ + 1:])
    lsf_telescope_model = "LCO" if parts[3][4:] == "s" else "APO"
    gd = dict(g="giant", d="dwarf")[gd]
    lsf = parts[3][3]
    return [lsf_telescope_model, lsf, f"{spectral_type}-{gd}"]


def yield_suitable_grids(grid_info, mean_fiber, teff, logg, metals, telescope, **kwargs):
    """
    Yield suitable FERRE grids given header information from an observation and a dictionary of grid limits.
    
    :param grid_info:
        A dictionary containing header paths as keys, and a three-length tuple as values: (1) metadata, (2) lower limits, (3) upper limits.
        This is the expected output from `parse_grid_information`.
    
    :param mean_fiber:
        The mean fiber number of observations.
    
    :param teff:
        An initial guess of the effective temperature.
    
    :param logg:
        An initial guess of the surface gravity.
    
    :param metals:
        An initial guess of the metallicity.
    
    :returns:
        A generator that yields two-length tuples containing header path, and metadata..
    """

    # Figure out which grids are suitable.
    lsf_grid = get_lsf_grid_name(int(np.round(mean_fiber)))

    point = np.array([metals, logg, teff])
    P = point.size
    
    for header_path, (meta, lower_limits, upper_limits) in grid_info.items():

        #print(meta["lsf"], lsf_grid, telescope, meta["lsf_telescope_model"], header_path)
        # Match star to LSF fiber number model (a, b, c, d) and telescope model (apo25m/lco25m).
        # TODO: This is a very APOGEE-specific thing and perhaps should be moved elsewhere.
        # Special case to deal with Kurucz photospheres.
        if (meta["lsf"] != lsf_grid and not meta["lsf"].startswith("combo")) or telescope != meta["lsf_telescope_model"]:
            continue

        # We will take the RV parameters as the initial parameters. 
        # Check to see if they are within bounds of the grid.
        if np.all(point >= lower_limits[-P:]) and np.all(point <= upper_limits[-P:]):
            yield (header_path, meta)


def get_lsf_grid_name(fibre_number):
    """
    Return the appropriate LSF name (a, b, c, or d) to use, given a mean fiber number.

    :param fiber_number:
        The mean fiber number of observations.
    
    :returns:
        A one-length string describing which LSF grid to use ('a', 'b', 'c', or 'd').
    """
    if 50 >= fibre_number >= 1:
        return "d"
    if 145 >= fibre_number > 50:
        return "c"
    if 245 >= fibre_number > 145:
        return "b"
    if 300 >= fibre_number > 245:
        return "a"


def parse_header_path(header_path):
    """
    Parse the path of a header file and return a dictionary of relevant parameters.

    :param header_path:
        The path of a grid header file.
    
    :returns:
        A dictionary of keywords that are relevant to running FERRE tasks.
    """

    *_, radiative_transfer_code, model_photospheres, isotopes, folder, basename = header_path.split("/")

    parts = basename.split("_")
    # p_apst{gd}{spectral_type}_{date}_lsf{lsf}_{aspcap}_012_075
    _ = 4
    gd, spectral_type = (parts[1][_], parts[1][_ + 1:])
    # Special case for the BA grid with kurucz atmospheres. Sigh.
    if gd == "B" and spectral_type == "A":
        year, month, day = (2019, 11, 21)
        lsf = "combo5"
        lsf_telescope_model = "lco25m" if parts[2].endswith("s") else "apo25m"
        is_giant_grid = False
        gd = ""
        spectral_type = "BA"

    else:
        date_str = parts[2]
        year, month, day = (2000 + int(date_str[:2]), int(date_str[2:4]), int(date_str[4:6]))
        lsf = parts[3][3]
        lsf_telescope_model = "lco25m" if parts[3][4:] == "s" else "apo25m"

        is_giant_grid = gd == "g"
    
    kwds = dict(
        radiative_transfer_code=radiative_transfer_code,
        model_photospheres=model_photospheres,
        isotopes=isotopes,
        gd=gd,
        lsf_telescope_model=lsf_telescope_model,
        spectral_type=spectral_type,
        grid_creation_date=datetime.date(year, month, day),
        lsf=lsf,
    )

    return kwds


def parse_grid_information(header_paths):
    """
    Parse the parameter limits of a pre-computed grid (e.g., in effective temperature) from grid header paths provided,
    and other possibly relevant information (e.g., telescope of the LSF model).

    :param header_paths:
        A list of paths that store information about pre-computed grids.
    
    :returns:
        A dictionary with paths as keys, and the value of the dictionary is a three-length tuple containing (1) metadata, (2) lower limits in parameters, (2) upper limits in parameters.
    """

    grids = {}
    for header_path in header_paths:
        
        full_header_path = os.path.expandvars(header_path)

        try:
            headers = read_ferre_headers(full_header_path)
            meta = parse_header_path(full_header_path)

        except:
            raise
    
        else:
            # Get grid limits.
            grids[header_path] = (meta, list(headers[0]["LLIMITS"]), list(headers[0]["ULIMITS"]))

    return grids


def approximate_log10_microturbulence(log_g):
    """
    Approximate the log10(microturbulent velocity) given the surface gravity.

    :param log_g:
        The surface gravity.
    
    :returns:
        The log base-10 of the microturbulent velocity, vt: log_10(vt).
    """

    coeffs = np.array([0.372160, -0.090531, -0.000802, 0.001263, -0.027321])
    # I checked with Holtz on this microturbulence relation because last term is not used.
    DM = np.array([1, log_g, log_g**2, log_g**3, 0])
    return DM @ coeffs


def get_abundance_keywords(element, header_label_names):
    """
    Return a dictionary of task parameters given a chemical element. These are adopted from DR16.

    :param element:
        The chemical element to measure.

    :param header_label_names:
        The list of label names in the FERRE header file.
    """

    # These can be inferred from running the following command on the SAS:
    # cd /uufs/chpc.utah.edu/common/home/sdss50/dr16/apogee/spectro/aspcap/r12/l33/apo25m/cal_all_apo25m007/ferre
    # egrep 'INDV|TIE|FILTERFILE' */input.nml
    
    controls = {
        "Al": {
            "INDV_LABEL": ('METALS', ),
            "TIES": [
                ('C', 0, -1),
                ('N', 0, -1),
                ('O Mg Si S Ca Ti', 0, -1)
            ]
        },
        "Ca": {
            "INDV_LABEL": ('O Mg Si S Ca Ti', ),
        },
        "Ce": {
            "INDV_LABEL": ('METALS', ),
        },
        "CI": {
            "INDV_LABEL": ('C', ),
        },
        "C": {
            "INDV_LABEL": ('C', ),
        },
        "CN": {
            "INDV_LABEL": ('C', 'O Mg Si S Ca Ti', ),
        },
        "Co": {
            "INDV_LABEL": ('METALS', ),
            "TIES": [
                ('C', 0, -1),
                ('N', 0, -1),
                ('O Mg Si S Ca Ti', 0, -1)
            ]    
        },
        "Cr": {
            "INDV_LABEL": ('METALS', ),
            "TIES": [
                ('C', 0, -1),
                ('N', 0, -1),
                ('O Mg Si S Ca Ti', 0, -1)
            ]
        },
        "Cu": {
            "INDV_LABEL": ('METALS', ),
            "TIES": [
                ('C', 0, -1),
                ('N', 0, -1),
                ('O Mg Si S Ca Ti', 0, -1)
            ]
        },
        "Fe": {
            "INDV_LABEL": ('METALS', ),
            "TIES": [
                ('C', 0, -1),
                ('N', 0, -1),
                ('O Mg Si S Ca Ti', 0, -1)
            ]
        },
        "Ge": {
            "INDV_LABEL": ('METALS', ),
            "TIES": [
                ('C', 0, -1),
                ('N', 0, -1),
                ('O Mg Si S Ca Ti', 0, -1)
            ]
        },
        "K": {
            "INDV_LABEL": ('METALS', ),
            "TIES": [
                ('C', 0, -1),
                ('N', 0, -1),
                ('O Mg Si S Ca Ti', 0, -1)
            ]
        },
        "Mg": {
            "INDV_LABEL": ('O Mg Si S Ca Ti', ),
        },
        "Mn": {
            "INDV_LABEL": ('METALS', ),
            "TIES": [
                ('C', 0, -1),
                ('N', 0, -1),
                ('O Mg Si S Ca Ti', 0, -1)
            ]
        },
        "Na": {
            "INDV_LABEL": ('METALS', ),
            "TIES": [
                ('C', 0, -1),
                ('N', 0, -1),
                ('O Mg Si S Ca Ti', 0, -1)
            ]
        },
        "Nd": {
            "INDV_LABEL": ('METALS', ),
            "TIES": [
                ('C', 0, -1),
                ('N', 0, -1),
                ('O Mg Si S Ca Ti', 0, -1)
            ]
        },
        "Ni": {
            "INDV_LABEL": ('METALS', ),
            "TIES": [
                ('C', 0, -1),
                ('N', 0, -1),
                ('O Mg Si S Ca Ti', 0, -1)
            ]
        },
        "N": {
            "INDV_LABEL": ('N', ),
        },
        "O": {
            "INDV_LABEL": ('O Mg Si S Ca Ti', ),
        },
        "P": {
            "INDV_LABEL": ('METALS', ),
            "TIES": [
                ('C', 0, -1),
                ('N', 0, -1),
                ('O Mg Si S Ca Ti', 0, -1)
            ]
        },
        "Rb": {
            "INDV_LABEL": ('METALS', ),
            "TIES": [
                ('C', 0, -1),
                ('N', 0, -1),
                ('O Mg Si S Ca Ti', 0, -1)
            ]
        },
        "Si": {
            "INDV_LABEL": ('O Mg Si S Ca Ti', ),
        },
        "S": {
            "INDV_LABEL": ('O Mg Si S Ca Ti', ),
        },
        "TiII": {
            "INDV_LABEL": ('O Mg Si S Ca Ti', ),
        },
        "Ti": {
            "INDV_LABEL": ('O Mg Si S Ca Ti', ),
        },
        "V": {
            "INDV_LABEL": ('METALS', ),
            "TIES": [
                ('C', 0, -1),
                ('N', 0, -1),
                ('O Mg Si S Ca Ti', 0, -1)
            ]
        },
        "Yb": {
            "INDV_LABEL": ('METALS', ),
            "TIES": [
                ('C', 0, -1),
                ('N', 0, -1),
                ('O Mg Si S Ca Ti', 0, -1)
            ]
        }
    }

    def get_header_index(label):
        # FERRE uses 1-indexing and Python uses 0-indexing.
        return 1 + header_label_names.index(label)

    try:
        c = controls[element]
    except:
        raise ValueError(f"no abundance controls known for element '{element}' (available: {tuple(controls.keys())}")

    indv = [get_header_index(label) for label in c["INDV_LABEL"]]
    ties = c.get("TIES", [])

    ferre_kwds = {
        # We don't pass INDV here because this will be determined from the
        # 'frozen_<param>' arguments to the FerreGivenSDSSApStarFile tasks
        #"INDV": [get_header_index(label) for label in c["INDV_LABEL"]],
        "NTIE": len(ties),
        "TYPETIE": 1
    }
    for i, (tie_label, ttie0, ttie) in enumerate(ties, start=1):
        ferre_kwds.update({
            f"INDTIE({i:.0f})": get_header_index(tie_label),
            f"TTIE0({i:.0f})": ttie0,
            # TODO: What if we don't want to tie it back to first INDV element?
            f"TTIE({i:.0f},{indv[0]:.0f})": ttie
        })
    
    # Freeze all other labels.
    frozen_parameters = { hln: (hln not in c["INDV_LABEL"]) for hln in header_label_names }

    return (frozen_parameters, ferre_kwds)