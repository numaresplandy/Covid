import ssl
import json
import dash
import pandas as pd 
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
import dash_core_components as dcc
import dash_html_components as html
from plotly.subplots import make_subplots
from dash.dependencies import Input, Output

ssl._create_default_https_context = ssl._create_unverified_context

app = dash.Dash(__name__)

# ------------------------------------------------------------------------------
# Functions

def create_dataframe(france_density_data):
        covid = pd.read_csv('https://www.data.gouv.fr/fr/datasets/r/63352e38-d353-4b54-bfd1-f1b3ee1cabd7', sep=";", parse_dates=True)
        density = pd.read_csv(france_density_data,dtype={'name_dep': str, 'dep': str, 'Superficie(km2)': float,'Population(milliers)': float,'Density(hab/km2)':float})
        covid = pd.merge(density, covid, on = ['dep'])
        for i in ['974','973','972','971']: 
            covid= covid.drop(covid[ covid['dep'] ==i].index, axis=0)
        covid['sum']= covid['hosp'] + covid['rea']
        covid['sum']=covid['sum'].astype('float64')
        np.seterr(divide = 'ignore')
        tmp = covid['sum'].copy()
        for i in range(len(tmp)): 
            if np.log(tmp[i])==float('-inf'):
                tmp.loc[i]=1
        np.seterr(divide = 'warn')
        covid['sum']=tmp
        covid['jour'] =pd.to_datetime(covid['jour']).dt.date
        covid = covid.set_index('jour')
        return covid

def getmarksDict():
    d2={}
    for i in days:
        tmp = days[i].split('-')
        if tmp[2] =='01': 
            d2[i]={'label':str('1 '+mois[tmp[1]]),'style':styleMarksSlider1}
        elif tmp[2] in ['15']:
            d2[i]={'label':str(tmp[2]+' '+mois[tmp[1]]),'style':styleMarksSlider2}
    return d2

def transform(date): 
    tmp = date.split('-')
    s = tmp[2] +' '+mois[tmp[1]]+' '+tmp[0]
    return s 

# ------------------------------------------------------------------------------
# CSS variables

colors = {
    'background': '#111111',
    'text': '#7FDBFF'}

styleMarksSlider1={'color': 'white','font-size':'16px','font-family':'Helvetica, sans-serif'}

styleMarksSlider2={'color': 'white','font-size':'15px','font-family':'Helvetica, sans-serif'}

styleMainDiv={
  'verticalAlign':'middle',
  'textAlign': 'center',
  'backgroundColor': colors['background'],
  'position':'fixed',
  'width':'100%',
  'height':'100%',
  'top':'0px',
  'left':'0px',
  'z-index':'1000'}

styleMainTitle={'text-align': 'center',
                'color':'white',
                'font-family':'Helvetica, sans-serif'}

styleSliderDiv={ 'margin-bottom':'20px' }

styleGraphDiv={ 'height':'83%' }

styleGraph ={'height':'100%'}

# ------------------------------------------------------------------------------
# Import and clean data 

covid = create_dataframe("Data/france_density_pop.csv")
france = json.load(open("Geojson/france_dep.geojson",'r'))

# ------------------------------------------------------------------------------
# Global Variables

mois = {'01':'January','02':'February','03':'March','04':'April','05':'May','06':'June','07':'July','08':'August','09':'September','10':'October','11':'November','12':'December'}
days = {int(i):str(j) for i,j in zip(range(len(covid.index.unique())), covid.index.unique())}
firstMonth ={}
firstMonth = getmarksDict()

# ------------------------------------------------------------------------------
# App layout

app.layout = html.Div(style=styleMainDiv,children=[

    html.H1("Covid patients hospitalized and in intensive care in France since March 2020", style=styleMainTitle),
    
    html.Div(style=styleSliderDiv ,children=[dcc.Slider(
        id='slct_day',
        min=0,
        max=len(covid.index.unique())-1,
        step=1,
        marks = firstMonth,
        included=False,
        value=0,
        )]),

    html.Div(style=styleGraphDiv ,children=[dcc.Graph(id='subplot', figure={},style =styleGraph )])

])

# ------------------------------------------------------------------------------
# Connect the Plotly graphs with Dash Components


@app.callback(
   Output(component_id='subplot', component_property='figure'),
    [Input(component_id='slct_day', component_property='value')]
)
def update_graph(option_slctd):

    covid2 = covid.copy()
    covid2 = covid2[covid2['sexe']==2]
    covid2 = covid2.loc[datetime.strptime(days[option_slctd], '%Y-%m-%d').date()]
    covid2 = covid2.sort_values(by=['Density(hab/km2)'])
    


    fig = make_subplots(
    rows=1, cols=2,
    column_widths=[0.35, 0.65],
    horizontal_spacing=0.03,
    specs=[[{"type": "Choroplethmapbox"}, {"type": "bar"}]])

    fig.add_trace(go.Bar(
        x=covid2['name_dep'],
        y=covid2['hosp'],
        name='Hospitalization',
        hovertemplate ="<b>Department : %{customdata[0]} </b><br><b>Pop. Density : %{customdata[4]} hab/km2</b><br><b>Hospitalization : %{customdata[6]} pers.</b>"+"<extra></extra>",
        customdata=covid2,
        marker_color='rgb(196, 102, 73)',
        showlegend =False),
        row=1, col=2)

    fig.add_trace(go.Bar(
        x=covid2['name_dep'],
        y=covid2['rea'],
        name='Intensive care',
        hovertemplate ="<b>Department : %{customdata[0]} </b><br><b>Pop. Density : %{customdata[4]} hab/km2</b><br><b>Intensive care : %{customdata[7]} pers.</b>"+"<extra></extra>",
        customdata=covid2,
        marker_color='rgb(89, 13, 31)',
        showlegend =False),
        row=1, col=2)

    fig.add_trace(go.Choroplethmapbox(geojson=france, 
                                        locations=covid2['dep'],
                                        z=np.log10(covid2['sum']),
                                        customdata=covid2,
                                        showscale=False,
                                        hovertemplate ="<b>Department : %{customdata[0]} </b><br><b>Pop. Density : %{customdata[4]} hab/km2</b><br><b>Hospitalization : %{customdata[6]} pers.</b><br><b>Intensive care : %{customdata[7]} pers.</b>"+"<extra></extra>",
                                        featureidkey="properties.code",                           
                                        colorscale="amp",
                                        showlegend = False,
                                        marker_opacity=0.8, 
                                        marker_line_width=0.3,
                                        name='europe_map'),
                                        row=1, col=1)

    fig.update_layout(mapbox_style="carto-positron",mapbox_zoom=4, mapbox_center = {"lat": 46.35, "lon": 2.55})
    fig.update_layout(title_text="Covid patients in France departments ordered by population density : <b>"+ transform(days[option_slctd])+'</b>')
    fig.update_layout(barmode='relative')
    fig.update_layout(template='plotly_dark')

    return fig

# ------------------------------------------------------------------------------
# Main Function 

if __name__ == '__main__':
    app.run_server(debug=True)