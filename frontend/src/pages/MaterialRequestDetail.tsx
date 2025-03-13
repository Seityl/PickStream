import React from 'react';
import {useParams} from 'react-router';

export default function MaterialRequestDetail() {
  const params = useParams()
  const materialRequest = params.material_request;

  return (
    <div>
      <p>{materialRequest}</p>
    </div>);
}
